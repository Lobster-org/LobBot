import asyncio
import logging
from html import escape
from app.modules.base import BaseModule
from app.modules.games import handlers  # noqa: F401
from app.modules.games.games import CoinFlipGame, Connect4Game, GuessNumberGame, HangmanGame, RockPaperScissorsGame, TicTacToeGame, TriviaGame
from app.modules.games.games.trivia import QUESTIONS
from app.modules.games.handlers import GamesMiddleware
from app.modules.games.registry import GameRegistry
from app.modules.games.router import router
from app.modules.games.services import BetCoordinator, GameService, GameSessionService, RewardTracker, RoundMatchService, TriviaService

logger = logging.getLogger(__name__)

class GamesModule(BaseModule):
    name = "games"; version = "1.1.0"; description = "Coin flip, guessing, RPS, trivia, Tic-Tac-Toe, and Connect 4."; enabled_by_default = False; core = False
    def __init__(self): self.service = None; self.rewards = None; self.bets = None; self._cleanup_task = None; self.bot = None
    async def setup(self, container, dispatcher):
        middleware = GamesMiddleware(lambda: self.service); router.message.middleware(middleware); router.callback_query.middleware(middleware); dispatcher.include_router(router)
    async def startup(self, container):
        self.bot = container.bot
        registry = GameRegistry()
        for game in (CoinFlipGame(), GuessNumberGame(), RockPaperScissorsGame(), TriviaGame(), TicTacToeGame(), Connect4Game(), HangmanGame()): registry.register(game)
        self.rewards = RewardTracker()
        self.bets = BetCoordinator(container.event_bus)
        self.service = GameService(registry, GameSessionService(), container.event_bus,
                                   matches=RoundMatchService(), rewards=self.rewards)
        self.service.bets = self.bets
        self.service.trivia = TriviaService(QUESTIONS)
        container.event_bus.subscribe(self.rewards.EVENT, self.rewards.receive)
        container.event_bus.subscribe(self.bets.RESPONSE, self.bets.receive)
        self._cleanup_task = asyncio.create_task(self._cleanup_expired(), name="games-match-cleanup")
        logger.info("Games runtime ready: games=%s", len(registry.all()))
    async def shutdown(self, container):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            await asyncio.gather(self._cleanup_task, return_exceptions=True)
            self._cleanup_task = None
        if self.service and self.bets:
            for match in self.service.matches.all():
                if getattr(match, "game_type", None) == "hangman":
                    try:
                        await container.bot.edit_message_text(
                            chat_id=match.chat_id, message_id=match.message_id,
                            text=f"✖️ Hangman ended because LobBot is restarting.\n\nThe secret was: <b>{escape(match.secret)}</b>",
                            parse_mode="HTML",
                        )
                    except Exception:
                        logger.exception("Failed to close Hangman during shutdown: match=%s", match.id)
                if getattr(match, "betting", False) and match.bets:
                    response = await self.bets.settle(
                        match.chat_id, match.id, match.bets, winner_id=None
                    )
                    if not response.get("ok"):
                        logger.error("Failed to refund RPS pot during shutdown: match=%s", match.id)
        if self.rewards: container.event_bus.unsubscribe(self.rewards.EVENT, self.rewards.receive)
        if self.bets:
            container.event_bus.unsubscribe(self.bets.RESPONSE, self.bets.receive)
            self.bets.clear()
        if self.service: self.service.clear()
        self.service = self.rewards = self.bets = self.bot = None; logger.info("Games runtime stopped")

    async def _cleanup_expired(self):
        while True:
            try:
                await asyncio.sleep(30)
                if not self.service: continue
                for match in self.service.matches.expired():
                    if getattr(match, "game_type", None) == "hangman":
                        try:
                            await self.bot.edit_message_text(
                                chat_id=match.chat_id, message_id=match.message_id,
                                text=f"⌛ Hangman expired.\n\nThe secret was: <b>{escape(match.secret)}</b>",
                                parse_mode="HTML",
                            )
                            await self.service.events.emit("game.completed", {
                                "chat_id": match.chat_id, "user_id": match.opponent_id,
                                "game": "hangman", "won": False,
                                "metadata": {"match_id": match.id, "expired": True},
                            })
                        finally:
                            self.service.matches.delete(match.id)
                        continue
                    if getattr(match, "betting", False) and match.bets:
                        response = await self.bets.settle(
                            match.chat_id, match.id, match.bets, winner_id=None
                        )
                        if not response.get("ok"):
                            logger.error("Failed to refund expired RPS pot: match=%s", match.id)
                            continue
                    self.service.matches.delete(match.id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Games match cleanup failed")
