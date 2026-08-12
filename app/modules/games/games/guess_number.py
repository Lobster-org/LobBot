from dataclasses import dataclass
from app.modules.games.config import GUESS_MAX_ATTEMPTS

@dataclass(frozen=True)
class GuessNumberGame:
    name: str = "guess"; command: str = "guess"; description: str = "Guess LobBot's secret number."
    def guess(self, target, value, attempts):
        if value == target: return "correct", True, True
        if attempts >= GUESS_MAX_ATTEMPTS: return "failed", False, True
        return ("low" if value < target else "high"), False, False
