import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(slots=True)
class PaginationSession:
    id: str
    owner_id: int
    chat_id: int
    kind: str
    items: list[Any]
    page_size: int
    created_at: datetime
    expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_pages(self) -> int:
        return max(1, (len(self.items) + self.page_size - 1) // self.page_size)

    def page(self, number: int) -> list[Any]:
        number = max(0, min(number, self.total_pages - 1))
        start = number * self.page_size
        return self.items[start:start + self.page_size]


class PaginationStore:
    """Bounded, expiring, owner-scoped interactive search sessions."""

    def __init__(self, ttl_seconds: int = 600, max_sessions: int = 1000, clock=None):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_sessions = max_sessions
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._sessions: dict[str, PaginationSession] = {}

    def create(self, owner_id: int, chat_id: int, kind: str, items: list[Any], *, page_size=10, metadata=None):
        self.cleanup()
        if len(self._sessions) >= self.max_sessions:
            oldest = min(self._sessions.values(), key=lambda value: value.created_at)
            self._sessions.pop(oldest.id, None)
        now = self.clock()
        session = PaginationSession(
            id=secrets.token_urlsafe(6), owner_id=owner_id, chat_id=chat_id,
            kind=kind, items=list(items), page_size=page_size,
            created_at=now, expires_at=now + self.ttl, metadata=dict(metadata or {}),
        )
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str, *, chat_id: int | None = None) -> PaginationSession | None:
        session = self._sessions.get(session_id)
        if not session:
            return None
        if session.expires_at <= self.clock() or (chat_id is not None and session.chat_id != chat_id):
            self._sessions.pop(session_id, None)
            return None
        return session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def cleanup(self) -> None:
        now = self.clock()
        for key in [key for key, value in self._sessions.items() if value.expires_at <= now]:
            self._sessions.pop(key, None)

    def clear(self) -> None:
        self._sessions.clear()
