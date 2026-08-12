from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class EconomyProfile:
    chat_id: int
    user_id: int
    xp: int = 0
    level: int = 0
    coins: int = 0
    daily_streak: int = 0
    last_daily_at: datetime | None = None
    games_played: int = 0
    games_won: int = 0
    achievements: list[str] = field(default_factory=list)

    @classmethod
    def from_document(cls, chat_id, user_id, document=None):
        document = document or {}
        return cls(chat_id, user_id, *(document.get(k, d) for k, d in (
            ("xp", 0), ("level", 0), ("coins", 0), ("daily_streak", 0),
            ("last_daily_at", None), ("games_played", 0), ("games_won", 0),
            ("achievements", []),
        )))
