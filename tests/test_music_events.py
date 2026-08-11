import pytest

from app.core.events import EventBus
from app.modules.music.events import (
    PLAYBACK_STOPPED,
    TRACK_FINISHED,
    TRACK_QUEUED,
    TRACK_SKIPPED,
    TRACK_STARTED,
)
from app.modules.music.models.queue import QueueItem
from app.modules.music.models.track import Track
from app.modules.music.services.playback_service import PlaybackService
from app.modules.music.services.queue_service import QueueService


class VoiceService:
    def __init__(self):
        self.played = []

    async def play(self, chat_id, file_path):
        self.played.append((chat_id, file_path))

    async def stop(self, chat_id):
        return None


def item(source_id, title, requested_by):
    return QueueItem(
        track=Track(
            source="youtube",
            source_id=source_id,
            title=title,
            file_path=f"storage/{source_id}.webm",
        ),
        requested_by=requested_by,
    )


@pytest.mark.asyncio
async def test_queue_start_and_stream_end_emit_music_events():
    bus = EventBus()
    received = []

    async def record(event):
        received.append(event)

    for event_name in (
        TRACK_QUEUED,
        TRACK_STARTED,
        TRACK_FINISHED,
    ):
        bus.subscribe(event_name, record)

    queue = QueueService(events=bus)
    playback = PlaybackService(
        queue,
        VoiceService(),
        events=bus,
    )
    first = item("one", "First", 10)
    second = item("two", "Second", 11)

    await queue.add(-20, first)
    await queue.add(-20, second)
    await playback.ensure_playing(-20)
    await playback.tasks[-20]
    await playback.handle_stream_end(-20)

    assert [event.name for event in received] == [
        TRACK_QUEUED,
        TRACK_QUEUED,
        TRACK_STARTED,
        TRACK_FINISHED,
        TRACK_STARTED,
    ]
    assert received[2].payload["track"] is first.track
    assert received[2].payload["requested_by"] == 10
    assert received[3].payload["track"] is first.track
    assert received[4].payload["track"] is second.track


@pytest.mark.asyncio
async def test_skip_and_stop_emit_after_state_changes():
    bus = EventBus()
    received = []

    async def record(event):
        received.append(event)

    for event_name in (
        TRACK_SKIPPED,
        PLAYBACK_STOPPED,
    ):
        bus.subscribe(event_name, record)

    queue = QueueService(events=bus)
    playback = PlaybackService(
        queue,
        VoiceService(),
        events=bus,
    )
    first = item("one", "First", 10)
    second = item("two", "Second", 11)

    await queue.add(-20, first)
    await queue.add(-20, second)
    await playback.ensure_playing(-20)
    await playback.tasks[-20]
    await playback.skip(-20)
    await playback.stop(-20)

    assert [event.name for event in received] == [
        TRACK_SKIPPED,
        PLAYBACK_STOPPED,
    ]
    assert received[0].payload["track"] is first.track
    assert received[1].payload["track"] is second.track
    assert received[1].payload["queued_count"] == 0
