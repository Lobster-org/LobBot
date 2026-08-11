import asyncio
import logging

from app.core.logging import configure_logging

from app.telegram.voice.lifecycle import (
    VoiceLifecycle
)

from app.telegram.voice.service import (
    VoiceChatService,
)


CHAT_ID = -1002082932733

AUDIO_FILE = (
    "storage/music/test.m4a"
)


logger = logging.getLogger(__name__)


async def main():
    configure_logging()

    voice = VoiceLifecycle()

    await voice.start()

    logger.info("Voice client started")

    service = VoiceChatService(
        voice.calls
    )

    await service.play(
        CHAT_ID,
        AUDIO_FILE,
    )

    logger.info("Playback started")

    await asyncio.sleep(
        10
    )

    await service.stop(
        CHAT_ID
    )

    await voice.stop()

if __name__ == "__main__":

    asyncio.run(main())
