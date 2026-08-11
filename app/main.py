import asyncio
import logging

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.events import event_bus
from app.core.modules import module_loader

from app.database.mongodb import mongodb

from app.telegram.client import bot, dispatcher
from app.telegram.voice.lifecycle import (
    VoiceLifecycle
)

from app.core.container import container
from app.telegram.voice.service import VoiceChatService

from app.modules.music.state import music_state
from app.modules.music.services.playback_service import (
    PlaybackService,
)

from app.telegram.voice.events import (
    VoiceEventHandler,
)

from app.modules.music.config import (
    MUSIC_STORAGE_PATH,
)


logger = logging.getLogger(__name__)


async def main():

    voice = None
    configure_logging(
        settings.LOG_LEVEL
    )

    logger.info(
        "LobBot starting: environment=%s database=%s",
        settings.ENVIRONMENT,
        settings.MONGO_DATABASE,
    )


    try:

        await mongodb.connect()

        await mongodb.initialize_indexes()

        music_state.configure(
            mongodb.get_database(),
            str(MUSIC_STORAGE_PATH),
        )

        await music_state.queues.restore()

        voice = VoiceLifecycle()

        await voice.start()

        container.voice_service = VoiceChatService(voice.calls)


        music_state.player = PlaybackService(
            queue_service=music_state.queues,
            voice_service=container.voice_service,
            music_service=music_state.music_service,
            events=event_bus,
        )

        music_state.voice_events = (
            VoiceEventHandler(
                voice_calls=voice.calls,
                playback_service=music_state.player,
            )
        )

        music_state.voice_events.register()

        await music_state.player.restore()

        await module_loader.setup(
            dispatcher
        )

        logger.info("LobBot ready")
        logger.info("Bot polling started")

        await dispatcher.start_polling(
            bot
        )

    except Exception:
        logger.exception(
            "LobBot application failure"
        )
        raise

    finally:
        logger.info("Bot polling stopping")

        if voice:
            try:
                await voice.stop()
            except Exception:
                logger.exception(
                    "Voice client shutdown failed"
                )

        try:
            await module_loader.shutdown()
            logger.info("Module shutdown complete")
        except Exception:
            logger.exception(
                "Module shutdown failed"
            )

        try:
            await bot.session.close()
            logger.info("Telegram bot session closed")
        except Exception:
            logger.exception(
                "Telegram bot session shutdown failed"
            )

        try:
            await mongodb.disconnect()
        except Exception:
            logger.exception(
                "MongoDB shutdown failed"
            )

        logger.info("LobBot shutdown complete")




if __name__ == "__main__":
    asyncio.run(main())
