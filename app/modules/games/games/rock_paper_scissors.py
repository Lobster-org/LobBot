import random
from dataclasses import dataclass

@dataclass(frozen=True)
class RockPaperScissorsGame:
    name: str = "rps"; command: str = "rps"; description: str = "Challenge LobBot at rock, paper, scissors."
    choices = ("rock", "paper", "scissors")
    def play(self, choice, chooser=None):
        if choice not in self.choices: raise ValueError("Invalid RPS choice")
        bot = (chooser or random.choice)(self.choices)
        if choice == bot: return bot, None
        return bot, (choice, bot) in {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
