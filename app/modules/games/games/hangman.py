from dataclasses import dataclass


@dataclass(frozen=True)
class HangmanGame:
    name: str = "hangman"
    command: str = "hangman"
    description: str = "Set a secret phrase privately for another player to guess."

    STAGES = (
        "  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========",
        "  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========",
        "  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========",
        "  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========",
        "  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========",
        "  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========",
        "  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========",
    )

    @staticmethod
    def normalize_secret(value: str) -> str:
        secret = " ".join(value.strip().split())
        if not 2 <= len(secret) <= 60:
            raise ValueError("The secret must contain 2–60 characters.")
        if not any(character.isalpha() for character in secret):
            raise ValueError("The secret must contain at least one letter.")
        return secret

    @staticmethod
    def masked(secret: str, guessed: set[str]) -> str:
        return " ".join(
            character if not character.isalpha() or character.lower() in guessed else "_"
            for character in secret
        )

    @staticmethod
    def solved(secret: str, guessed: set[str]) -> bool:
        return all(not character.isalpha() or character.lower() in guessed for character in secret)

    @classmethod
    def drawing(cls, wrong_guesses: int) -> str:
        return cls.STAGES[max(0, min(wrong_guesses, len(cls.STAGES) - 1))]
