import logging
import random
from time import monotonic
from app.modules.games.config import COOLDOWNS, GUESS_MAX, GUESS_MIN
from app.modules.games.events import GAME_COMPLETED, GAME_LOST, GAME_STARTED, GAME_WON
from app.modules.games.models.result import GameResult

logger = logging.getLogger(__name__)

class CooldownActive(ValueError): pass

class GameService:
    def __init__(self, registry, sessions, events, randomizer=None, clock=None, matches=None, rewards=None):
        self.registry, self.sessions, self.events = registry, sessions, events
        self.randomizer = randomizer or random; self.clock = clock or monotonic; self._cooldowns = {}
        self.matches = matches
        self.rewards = rewards
    def check_cooldown(self, chat_id, user_id, game):
        key = (chat_id, user_id, game); now = self.clock(); ready = self._cooldowns.get(key, 0)
        if now < ready: raise CooldownActive(f"Try again in {ready-now:.1f}s")
        self._cooldowns[key] = now + COOLDOWNS[game]
    async def started(self, chat_id, user_id, game): await self.events.emit(GAME_STARTED, {"chat_id": chat_id, "user_id": user_id, "game": game})
    async def finish(self, result: GameResult):
        payload = {"chat_id": result.chat_id, "user_id": result.user_id, "game": result.game, "won": result.won, "score": result.score, "metadata": result.metadata}
        await self.events.emit(GAME_COMPLETED, payload)
        if result.won is True: await self.events.emit(GAME_WON, payload)
        elif result.won is False: await self.events.emit(GAME_LOST, payload)
        logger.debug("Game completed: game=%s chat=%s user=%s won=%s", result.game, result.chat_id, result.user_id, result.won)
    async def coinflip(self, chat_id, user_id, prediction=None):
        self.check_cooldown(chat_id, user_id, "coinflip"); await self.started(chat_id, user_id, "coinflip")
        outcome, won = self.registry.get("coinflip").play(prediction, self.randomizer.choice)
        result = GameResult("coinflip", chat_id, user_id, won, metadata={"outcome": outcome}); await self.finish(result); return result
    async def start_guess(self, chat_id, user_id):
        self.check_cooldown(chat_id, user_id, "guess"); target = self.randomizer.randint(GUESS_MIN, GUESS_MAX)
        self.sessions.create(chat_id, user_id, "guess", {"target": target, "attempts": 0}); await self.started(chat_id, user_id, "guess")
    async def guess(self, chat_id, user_id, value):
        session = self.sessions.get(chat_id, user_id, "guess")
        if not session: return None
        attempts = session.state["attempts"] + 1; status, won, complete = self.registry.get("guess").guess(session.state["target"], value, attempts)
        session.state["attempts"] = attempts
        if complete:
            self.sessions.delete(chat_id, user_id, "guess"); await self.finish(GameResult("guess", chat_id, user_id, won, score=attempts, metadata={"target": session.state["target"]}))
        return status, attempts, session.state["target"] if complete else None
    def clear(self):
        self.sessions.clear(); self._cooldowns.clear()
        if self.matches: self.matches.clear()
        if self.rewards: self.rewards.clear()
