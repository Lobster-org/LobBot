import logging

from aiogram import BaseMiddleware


logger = logging.getLogger(__name__)


class DebugMiddleware(
    BaseMiddleware
):

    async def __call__(
        self,
        handler,
        event,
        data,
    ):

        logger.debug(
            "Telegram update received: type=%s",
            type(event).__name__,
        )


        return await handler(
            event,
            data,
        )
