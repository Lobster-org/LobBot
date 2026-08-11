import asyncio
import logging

from app.core.logging import configure_logging

from app.telegram.voice.lifecycle import (
    VoiceLifecycle,
)

from app.telegram.voice.service import (
    VoiceChatService,
)

from app.telegram.voice.events import (
    VoiceEventHandler,
)

from app.modules.music.services.queue_service import (
    QueueService,
)

from app.modules.music.services.playback_service import (
    PlaybackService,
)

from app.modules.music.models.queue import (
    QueueItem,
)

from app.modules.music.models.track import (
    Track,
)


CHAT_ID = -1002082932733


logger = logging.getLogger(__name__)


async def main():

    configure_logging()

    voice = VoiceLifecycle()

    await voice.start()


    voice_service = VoiceChatService(
        voice.calls
    )


    queues = QueueService()


    playback = PlaybackService(
        queue_service=queues,
        voice_service=voice_service,
    )


    events = VoiceEventHandler(
        voice_calls=voice.calls,
        playback_service=playback,
    )

    events.register()


    track1 = Track(
        title="Test Track 1",
        file_path=(
            "storage/music/test1.mp3"
        ),
    )


    track2 = Track(
        title="Test Track 2",
        file_path=(
            "storage/music/test2.mp3"
        ),
    )


    await queues.add(
        chat_id=CHAT_ID,
        item=QueueItem(
            track=track1,
            requested_by=0,
        ),
    )


    await queues.add(
        chat_id=CHAT_ID,
        item=QueueItem(
            track=track2,
            requested_by=0,
        ),
    )


    await playback.ensure_playing(
        CHAT_ID
    )


    logger.info("Queue playback started")


    # Keep application alive.
    while True:

        await asyncio.sleep(5)


if __name__ == "__main__":

    asyncio.run(main())
