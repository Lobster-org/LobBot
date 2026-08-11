from aiogram import BaseMiddleware


class CommunityServiceMiddleware(BaseMiddleware):
    def __init__(self, getter):
        self.getter = getter

    async def __call__(self, handler, event, data):
        service = self.getter()
        if service is None:
            raise RuntimeError("Community service is not initialized")
        data["community_service"] = service
        return await handler(event, data)
