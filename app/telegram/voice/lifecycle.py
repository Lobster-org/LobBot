import logging

from app.telegram.voice.client import (
    create_voice_client,
)

logger = logging.getLogger(__name__)


class VoiceLifecycle:

    def __init__(self):

        self.client = None
        self.calls = None


    async def start(self):

        logger.info("Starting Telegram voice client")

        self.client, self.calls = (
            create_voice_client()
        )

        await self.client.start()

        me = await self.client.get_me()

        logger.info(
            "Voice client authenticated: user=%s username=%s",
            me.id,
            me.username,
        )

        await self.calls.start()

        logger.info("PyTgCalls voice engine ready")


    async def stop(self):

        if self.client:
            await self.client.disconnect()
        logger.info("Telegram voice client disconnected")
