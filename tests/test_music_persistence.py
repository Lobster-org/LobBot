import asyncio
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.modules.music.models.queue import QueueItem
from app.modules.music.models.track import Track
from app.modules.music.services.music_service import MusicService
from app.modules.music.services.playback_service import PlaybackService
from app.modules.music.services.queue_service import QueueService


class FakeQueueRepository:

    def __init__(self, documents=None):
        self.documents = {
            document["chat_id"]: deepcopy(document)
            for document in (documents or [])
        }

    async def save(self, chat_id, current, queue):
        self.documents[chat_id] = {
            "chat_id": chat_id,
            "current": deepcopy(current),
            "queue": deepcopy(queue),
        }

    async def delete(self, chat_id):
        self.documents.pop(chat_id, None)

    async def load_active(self):
        return [
            deepcopy(document)
            for document in self.documents.values()
        ]


class FailingQueueRepository(FakeQueueRepository):

    async def save(self, chat_id, current, queue):
        raise RuntimeError("mongodb unavailable")


class FakeVoiceService:

    def __init__(self):
        self.played = []

    async def play(self, chat_id, file_path):
        self.played.append((chat_id, file_path))


class FailingVoiceService:

    async def play(self, chat_id, file_path):
        raise RuntimeError("voice chat unavailable")


class FakeCacheUsageService:

    def __init__(self):
        self.used = []

    async def mark_used(self, track):
        self.used.append(track.source_id)


class SingleFlightMusicService(MusicService):

    def __init__(self):
        self._preparations = {}
        self._preparations_lock = asyncio.Lock()
        self.download_count = 0

    async def get_cached(self, track):
        return None

    async def download(self, track):
        self.download_count += 1
        await asyncio.sleep(0)
        track.file_path = f"{track.source_id}.webm"
        return track.file_path


def queue_item(title, source_id):
    return QueueItem(
        track=Track(
            title=title,
            source="youtube",
            source_id=source_id,
            file_path=f"storage/music/{source_id}.webm",
        ),
        requested_by=42,
        requested_at=datetime.now(timezone.utc),
    )


async def test_queue_mutations_are_persisted():
    repository = FakeQueueRepository()
    queues = QueueService(repository)
    chat_id = -1001

    await queues.add(chat_id, queue_item("Song A", "a"))
    await queues.add(chat_id, queue_item("Song B", "b"))

    document = repository.documents[chat_id]
    assert document["current"] is None
    assert [item["source_id"] for item in document["queue"]] == [
        "a",
        "b",
    ]

    current = await queues.next(chat_id)
    assert current.track.source_id == "a"
    assert repository.documents[chat_id]["current"]["source_id"] == "a"

    await queues.remove(chat_id, 0)
    assert repository.documents[chat_id]["queue"] == []

    await queues.clear(chat_id)
    assert chat_id not in repository.documents


async def test_failed_persistence_rolls_back_queue_mutation():
    queues = QueueService(FailingQueueRepository())
    chat_id = -1001

    with pytest.raises(RuntimeError, match="mongodb unavailable"):
        await queues.add(
            chat_id,
            queue_item("Song A", "a"),
        )

    assert queues.snapshot(chat_id).items == []


async def test_restore_requeues_interrupted_current_track_first():
    current = QueueService._serialize_item(
        queue_item("Song A", "a")
    )
    queued = QueueService._serialize_item(
        queue_item("Song B", "b")
    )
    repository = FakeQueueRepository(
        [
            {
                "chat_id": -1001,
                "current": current,
                "queue": [queued],
            }
        ]
    )
    queues = QueueService(repository)

    restored = await queues.restore()
    snapshot = queues.snapshot(-1001)

    assert restored == [-1001]
    assert snapshot.current is None
    assert [item.track.source_id for item in snapshot.items] == [
        "a",
        "b",
    ]


async def test_playback_updates_cache_last_used_through_music_service():
    queues = QueueService(FakeQueueRepository())
    voice = FakeVoiceService()
    usage = FakeCacheUsageService()
    playback = PlaybackService(queues, voice, usage)
    chat_id = -1001

    await queues.add(chat_id, queue_item("Song A", "a"))
    await playback.ensure_playing(chat_id)
    await playback.tasks[chat_id]

    assert usage.used == ["a"]


async def test_concurrent_preparation_downloads_track_once():
    service = SingleFlightMusicService()
    tracks = [
        Track(
            title="Song A",
            source="youtube",
            source_id="a",
        )
        for _ in range(2)
    ]

    prepared = await asyncio.gather(
        *(service.prepare(track) for track in tracks)
    )

    assert service.download_count == 1
    assert [track.file_path for track in prepared] == [
        "a.webm",
        "a.webm",
    ]


async def test_voice_failure_preserves_track_for_retry():
    repository = FakeQueueRepository()
    queues = QueueService(repository)
    playback = PlaybackService(
        queues,
        FailingVoiceService(),
    )
    chat_id = -1001

    await queues.add(chat_id, queue_item("Song A", "a"))
    await queues.add(chat_id, queue_item("Song B", "b"))
    await playback.ensure_playing(chat_id)
    await playback.tasks[chat_id]

    snapshot = queues.snapshot(chat_id)
    assert snapshot.current is None
    assert snapshot.is_playing is False
    assert [item.track.source_id for item in snapshot.items] == [
        "a",
        "b",
    ]
    assert [
        item["source_id"]
        for item in repository.documents[chat_id]["queue"]
    ] == ["a", "b"]
