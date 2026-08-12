from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class GameSession:
    chat_id: int
    user_id: int
    game_type: str
    state: dict = field(default_factory=dict)
    created_at: datetime | None = None
    expires_at: datetime | None = None
