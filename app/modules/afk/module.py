from app.modules.afk.handlers import AFKMiddleware, router
from app.modules.afk.repository import AFKRepository
from app.modules.afk.service import AFKService
from app.modules.base import BaseModule


class AFKModule(BaseModule):
    name = "afk"; version = "1.0.0"; description = "Group-scoped AFK, BRB, and missed mentions."; enabled_by_default = False; core = False
    def __init__(self): self.service = None
    async def setup(self, container, dispatcher): router.message.middleware(AFKMiddleware(lambda: self.service)); dispatcher.include_router(router)
    async def startup(self, container): self.service = AFKService(AFKRepository(container.database), container.event_bus)
    async def shutdown(self, container):
        if self.service: self.service.shutdown()
        self.service = None
