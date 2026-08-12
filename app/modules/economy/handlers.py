from aiogram import BaseMiddleware


class EconomyMiddleware(BaseMiddleware):
    def __init__(self, getter): self.getter = getter
    async def __call__(self, handler, event, data):
        service = self.getter()
        if service is None: raise RuntimeError("Economy service is not initialized")
        data["economy_service"] = service
        return await handler(event, data)
