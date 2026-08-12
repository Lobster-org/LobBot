from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EconomyTransaction:
    chat_id: int
    user_id: int
    type: str
    amount: int
    reason: str
    metadata: dict = field(default_factory=dict)
