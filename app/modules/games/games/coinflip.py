import random
from dataclasses import dataclass

@dataclass(frozen=True)
class CoinFlipGame:
    name: str = "coinflip"; command: str = "coinflip"; description: str = "Flip a coin and predict the outcome."
    def play(self, prediction=None, chooser=None):
        if prediction is not None and prediction not in {"heads", "tails"}: raise ValueError("Choose heads or tails")
        result = (chooser or random.choice)(("heads", "tails"))
        return result, None if prediction is None else result == prediction
