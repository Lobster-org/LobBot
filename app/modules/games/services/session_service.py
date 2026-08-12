from datetime import datetime, timedelta, timezone
from app.modules.games.config import SESSION_TIMEOUT_SECONDS
from app.modules.games.models.session import GameSession


class GameSessionService:
    def __init__(self, timeout=SESSION_TIMEOUT_SECONDS, clock=None):
        self.timeout = timeout; self.clock = clock or (lambda: datetime.now(timezone.utc)); self._sessions = {}
    def create(self, chat_id, user_id, game_type, state=None):
        now = self.clock(); session = GameSession(chat_id, user_id, game_type, state or {}, now, now + timedelta(seconds=self.timeout))
        self._sessions[(chat_id, user_id, game_type)] = session; return session
    def get(self, chat_id, user_id, game_type):
        key = (chat_id, user_id, game_type); session = self._sessions.get(key)
        if session and session.expires_at <= self.clock(): self._sessions.pop(key, None); return None
        return session
    def update(self, chat_id, user_id, game_type, **state):
        session = self.get(chat_id, user_id, game_type)
        if session: session.state.update(state)
        return session
    def delete(self, chat_id, user_id, game_type): return self._sessions.pop((chat_id, user_id, game_type), None)
    def expire(self):
        now = self.clock(); expired = [key for key, value in self._sessions.items() if value.expires_at <= now]
        for key in expired: self._sessions.pop(key, None)
        return len(expired)
    def clear(self): self._sessions.clear()
