import asyncio
import logging

from app.core.config import settings
from app.core.container import container
from app.core.logging import configure_logging
from app.core.http import HttpClient
from app.core.modules import module_loader
from app.modules.registry import register_modules
from app.telegram.client import bot, dispatcher
from app.telegram.voice.lifecycle import VoiceLifecycle
from app.telegram.voice.service import VoiceChatService


logger = logging.getLogger(__name__)


async def main():
    configure_logging(settings.LOG_LEVEL)
    register_modules(module_loader)

    logger.info(
        "LobBot starting: environment=%s database=%s",
        settings.ENVIRONMENT,
        settings.MONGO_DATABASE,
    )

    try:
        await container.mongodb.connect()
        await container.mongodb.initialize_indexes()
        container.set_database(
            container.mongodb.get_database()
        )
        container.bot = bot

        container.http_client = HttpClient(
            user_agent=settings.HTTP_USER_AGENT,
            timeout_seconds=settings.HTTP_TIMEOUT_SECONDS,
        )
        await container.http_client.start()

        container.voice_lifecycle = VoiceLifecycle()
        await container.voice_lifecycle.start()
        container.voice_service = VoiceChatService(
            container.voice_lifecycle.calls
        )

        await module_loader.setup(container, dispatcher)
        await module_loader.startup(container)

        logger.info("LobBot ready")
        logger.info("Bot polling started")
        await dispatcher.start_polling(bot)
    except Exception:
        logger.exception("LobBot application failure")
        raise
    finally:
        logger.info("Bot polling stopping")

        await module_loader.shutdown(container)
        logger.info("Module shutdown complete")

        if container.voice_lifecycle:
            try:
                await container.voice_lifecycle.stop()
            except Exception:
                logger.exception("Voice client shutdown failed")

        if container.http_client:
            try:
                await container.http_client.close()
            except Exception:
                logger.exception("Shared HTTP client shutdown failed")

        try:
            await bot.session.close()
            logger.info("Telegram bot session closed")
        except Exception:
            logger.exception("Telegram bot session shutdown failed")

        try:
            await container.mongodb.disconnect()
        except Exception:
            logger.exception("MongoDB shutdown failed")

        container.clear_runtime()
        logger.info("LobBot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
