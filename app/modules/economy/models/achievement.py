from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Achievement:
    id: str
    name: str
    description: str
