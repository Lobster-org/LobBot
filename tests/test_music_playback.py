from app.modules.music.models.queue import QueueItem
from app.modules.music.models.track import Track
from app.modules.music.services.playback_service import PlaybackService
from app.modules.music.services.queue_service import QueueService


class FakeVoiceService:

    def __init__(self):
        self.played = []
        self.paused = []
        self.resumed = []
        self.stopped = []

    async def play(self, chat_id, file_path):
        self.played.append((chat_id, file_path))

    async def stop(self, chat_id):
        self.stopped.append(chat_id)

    async def pause(self, chat_id):
        self.paused.append(chat_id)

    async def resume(self, chat_id):
        self.resumed.append(chat_id)


async def test_ensure_playing_sends_first_queued_track_to_voice():
    chat_id = -1001
    queues = QueueService()
    voice = FakeVoiceService()
    playback = PlaybackService(queues, voice)

    await queues.add(
        chat_id,
        QueueItem(
            track=Track(
                title="Blinding Lights",
                file_path="/tmp/blinding-lights.webm",
            ),
            requested_by=42,
        ),
    )

    await playback.ensure_playing(chat_id)
    await playback.tasks[chat_id]

    queue = queues.get(chat_id)
    assert voice.played == [
        (chat_id, "/tmp/blinding-lights.webm")
    ]
    assert queue.current.track.title == "Blinding Lights"
    assert queue.is_playing is True


async def test_song_requested_during_playback_waits_for_stream_end():
    chat_id = -1001
    queues = QueueService()
    voice = FakeVoiceService()
    playback = PlaybackService(queues, voice)

    await queues.add(
        chat_id,
        QueueItem(
            track=Track(
                title="Song A",
                file_path="/tmp/song-a.webm",
            ),
            requested_by=42,
        ),
    )

    await playback.ensure_playing(chat_id)
    await playback.tasks[chat_id]

    await queues.add(
        chat_id,
        QueueItem(
            track=Track(
                title="Song B",
                file_path="/tmp/song-b.webm",
            ),
            requested_by=43,
        ),
    )
    await playback.ensure_playing(chat_id)

    assert voice.played == [
        (chat_id, "/tmp/song-a.webm")
    ]
    assert queues.get(chat_id).current.track.title == "Song A"
    assert queues.get(chat_id).items[0].track.title == "Song B"

    await playback.handle_stream_end(chat_id)

    assert voice.played == [
        (chat_id, "/tmp/song-a.webm"),
        (chat_id, "/tmp/song-b.webm"),
    ]
    assert queues.get(chat_id).current.track.title == "Song B"


async def test_pause_and_resume_update_voice_and_queue_state():
    chat_id = -1001
    queues = QueueService()
    voice = FakeVoiceService()
    playback = PlaybackService(queues, voice)

    await queues.add(
        chat_id,
        QueueItem(
            track=Track(
                title="Song A",
                file_path="song-a.webm",
            ),
            requested_by=42,
        ),
    )
    await playback.ensure_playing(chat_id)
    await playback.tasks[chat_id]

    assert await playback.pause(chat_id) is True
    assert queues.get(chat_id).is_paused is True
    assert voice.paused == [chat_id]

    assert await playback.resume(chat_id) is True
    assert queues.get(chat_id).is_paused is False
    assert voice.resumed == [chat_id]


async def test_skip_starts_next_track():
    chat_id = -1001
    queues = QueueService()
    voice = FakeVoiceService()
    playback = PlaybackService(queues, voice)

    for title in ("Song A", "Song B"):
        await queues.add(
            chat_id,
            QueueItem(
                track=Track(
                    title=title,
                    file_path=f"{title}.webm",
                ),
                requested_by=42,
            ),
        )

    await playback.ensure_playing(chat_id)
    await playback.tasks[chat_id]
    skipped = await playback.skip(chat_id)

    assert skipped.track.title == "Song A"
    assert queues.get(chat_id).current.track.title == "Song B"
    assert voice.played[-1] == (chat_id, "Song B.webm")


async def test_stop_clears_queue_and_leaves_voice_chat():
    chat_id = -1001
    queues = QueueService()
    voice = FakeVoiceService()
    playback = PlaybackService(queues, voice)

    await queues.add(
        chat_id,
        QueueItem(
            track=Track(
                title="Song A",
                file_path="song-a.webm",
            ),
            requested_by=42,
        ),
    )
    await playback.ensure_playing(chat_id)
    await playback.tasks[chat_id]

    assert await playback.stop(chat_id) is True
    assert queues.get(chat_id).current is None
    assert queues.get(chat_id).items == []
    assert queues.get(chat_id).is_playing is False
    assert voice.stopped == [chat_id]
