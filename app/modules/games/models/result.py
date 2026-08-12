from dataclasses import dataclass, field


@dataclass(slots=True)
class GameResult:
    game: str
    chat_id: int
    user_id: int
    won: bool | None
    score: int | None = None
    metadata: dict = field(default_factory=dict)
