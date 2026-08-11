from aiogram import BaseMiddleware


class WelcomeServiceMiddleware(BaseMiddleware):
    def __init__(self, service_getter):
        self.service_getter = service_getter

    async def __call__(self, handler, event, data):
        service = self.service_getter()
        if service is None:
            raise RuntimeError("Welcome service is not initialized")
        data["welcome_service"] = service
        return await handler(event, data)
