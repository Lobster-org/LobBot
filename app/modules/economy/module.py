import logging
from app.modules.base import BaseModule
from app.modules.economy import commands  # noqa: F401
from app.modules.economy.events import GAME_COMPLETED, GAME_WON
from app.modules.economy.handlers import EconomyMiddleware
from app.modules.economy.listeners import EconomyListeners
from app.modules.economy.repositories.profile_repository import EconomySettingsRepository, ProfileRepository
from app.modules.economy.repositories.transaction_repository import TransactionRepository
from app.modules.economy.repositories.bet_repository import BetRepository
from app.modules.economy.router import router
from app.modules.economy.services.economy_service import EconomyService

logger = logging.getLogger(__name__)


class EconomyModule(BaseModule):
    name = "economy"; version = "1.0.0"; description = "Per-group XP, coins, streaks, achievements, and leaderboards."; enabled_by_default = False; core = False
    def __init__(self): self.service = None; self.listeners = None
    async def setup(self, container, dispatcher):
        router.message.middleware(EconomyMiddleware(lambda: self.service)); dispatcher.include_router(router)
    async def startup(self, container):
        self.service = EconomyService(ProfileRepository(container.database), TransactionRepository(container.database), EconomySettingsRepository(container.database), container.event_bus)
        self.listeners = EconomyListeners(self.service, container.database, bets=BetRepository(container.database))
        recovered = await self.listeners.recover_unsettled_bets()
        if recovered: logger.warning("Recovered and refunded unsettled RPS bets: count=%s", recovered)
        container.event_bus.subscribe(GAME_COMPLETED, self.listeners.completed); container.event_bus.subscribe(GAME_WON, self.listeners.won)
        container.event_bus.subscribe(self.listeners.BET_REQUEST, self.listeners.bet_requested)
        container.event_bus.subscribe(self.listeners.BET_SETTLE, self.listeners.bet_settlement)
        logger.info("Economy runtime ready")
    async def shutdown(self, container):
        if self.listeners:
            container.event_bus.unsubscribe(GAME_COMPLETED, self.listeners.completed); container.event_bus.unsubscribe(GAME_WON, self.listeners.won)
            container.event_bus.unsubscribe(self.listeners.BET_REQUEST, self.listeners.bet_requested)
            container.event_bus.unsubscribe(self.listeners.BET_SETTLE, self.listeners.bet_settlement)
        self.service = self.listeners = None; logger.info("Economy runtime stopped")
