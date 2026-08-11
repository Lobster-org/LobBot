import logging

from app.modules.base import BaseModule
from app.modules.community import commands, handlers  # noqa: F401
from app.modules.community.filters import CommunityServiceMiddleware
from app.modules.community.repositories.community_repository import CommunityRepository, VerificationRepository
from app.modules.community.router import router
from app.modules.community.services import CommunityService, VerificationService


logger = logging.getLogger(__name__)


class CommunityModule(BaseModule):
    name = "community"
    version = "1.0.0"
    description = "Welcomes, goodbyes, rules, and newcomer verification."
    enabled_by_default = False
    core = False

    def __init__(self):
        self.service = None

    async def setup(self, container, dispatcher):
        middleware = CommunityServiceMiddleware(lambda: self.service)
        router.message.middleware(middleware)
        router.callback_query.middleware(middleware)
        dispatcher.include_router(router)

    async def startup(self, container):
        if container.database is None or container.bot is None:
            raise RuntimeError("Community requires the database and Telegram bot")
        verification = VerificationService(VerificationRepository(container.database), container.bot, container.event_bus)
        self.service = CommunityService(CommunityRepository(container.database), verification, container.bot, container.event_bus)
        await verification.start()
        logger.info("Community runtime ready")

    async def shutdown(self, container):
        if self.service:
            await self.service.verification.stop()
        self.service = None
        logger.info("Community runtime stopped")
