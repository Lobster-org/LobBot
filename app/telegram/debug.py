from aiogram import BaseMiddleware


class DebugMiddleware(
    BaseMiddleware
):

    async def __call__(
        self,
        handler,
        event,
        data,
    ):

        print(
            "UPDATE:",
            type(event).__name__,
        )


        return await handler(
            event,
            data,
        )