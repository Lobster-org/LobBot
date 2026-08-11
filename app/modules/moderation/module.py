import logging

from app.modules.base import BaseModule
from app.modules.moderation import commands  # noqa: F401
from app.modules.moderation.events import MODERATION_EVENTS
from app.modules.moderation.filters import ModerationServiceMiddleware
from app.modules.moderation.repositories.moderation_repository import (
    AutomodRepository,
    ModerationRepository,
)
from app.modules.moderation.router import router
from app.modules.moderation.services.moderation_service import (
    ModerationService,
)
from app.modules.moderation.services.punishment_service import (
    PunishmentService,
)
from app.modules.moderation.services.automod_service import AutomodService


logger = logging.getLogger(__name__)


class ModerationModule(BaseModule):
    name = "moderation"
    version = "1.0.0"
    description = "Warnings, automated filters, mutes, bans, and cleanup."
    enabled_by_default = False
    core = False

    def __init__(self):
        self.service: ModerationService | None = None
        self.automod: AutomodService | None = None
        self._event_listener = self._log_moderation_event

    async def setup(self, container, dispatcher):
        router.message.middleware(
            ModerationServiceMiddleware(
                lambda: self.service,
                lambda: self.automod,
            )
        )
        router.callback_query.middleware(
            ModerationServiceMiddleware(
                lambda: self.service,
                lambda: self.automod,
            )
        )
        dispatcher.include_router(router)

    async def startup(self, container):
        if container.database is None:
            raise RuntimeError("Moderation requires an active database")
        if container.bot is None:
            raise RuntimeError("Moderation requires the Telegram bot")

        self.service = ModerationService(
            repository=ModerationRepository(container.database),
            punishments=PunishmentService(container.bot),
            events=container.event_bus,
        )
        self.automod = AutomodService(
            repository=AutomodRepository(container.database),
            moderation_service=self.service,
            bot=container.bot,
            events=container.event_bus,
        )
        await self.service.start()

        for event_name in MODERATION_EVENTS:
            container.event_bus.subscribe(
                event_name,
                self._event_listener,
            )

        logger.info("Moderation runtime ready")

    async def shutdown(self, container):
        if self.service:
            await self.service.stop()
        if self.automod:
            self.automod.clear()

        for event_name in MODERATION_EVENTS:
            container.event_bus.unsubscribe(
                event_name,
                self._event_listener,
            )

        self.service = None
        self.automod = None
        logger.info("Moderation runtime stopped")

    async def _log_moderation_event(self, event):
        payload = event.payload
        logger.info(
            "Moderation event: event=%s action=%s chat=%s user=%s "
            "moderator=%s action_id=%s",
            event.name,
            payload.get("action"),
            payload.get("chat_id"),
            payload.get("user_id"),
            payload.get("moderator_id"),
            payload.get("action_id"),
        )
