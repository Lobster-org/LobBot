from app.modules.base import BaseModule
from app.modules.welcome.filters import WelcomeServiceMiddleware
from app.modules.welcome.handler import router
from app.modules.welcome.service import WelcomeService


class WelcomeModule(BaseModule):
    name = "welcome"
    version = "1.0.0"
    description = "Fun randomized introductions for new group members."
    enabled_by_default = False
    core = False

    def __init__(self):
        self.service = None

    async def setup(self, container, dispatcher):
        router.message.middleware(
            WelcomeServiceMiddleware(lambda: self.service)
        )
        dispatcher.include_router(router)

    async def startup(self, container):
        if container.bot is None:
            raise RuntimeError("Welcome requires the Telegram bot")
        self.service = WelcomeService(
            container.bot,
            container.event_bus,
        )

    async def shutdown(self, container):
        self.service = None
