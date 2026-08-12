import random
from dataclasses import dataclass

QUESTIONS = (
    {"question": "What does CPU stand for?", "choices": ("Central Processing Unit", "Computer Personal Unit", "Core Program Utility", "Central Power User"), "answer": 0, "category": "technology", "difficulty": "easy"},
    {"question": "Which planet is known as the Red Planet?", "choices": ("Venus", "Mars", "Jupiter", "Mercury"), "answer": 1, "category": "science", "difficulty": "easy"},
    {"question": "Who wrote Hamlet?", "choices": ("Austen", "Homer", "Shakespeare", "Orwell"), "answer": 2, "category": "literature", "difficulty": "easy"},
    {"question": "Binary 1010 equals which decimal number?", "choices": ("8", "10", "12", "14"), "answer": 1, "category": "technology", "difficulty": "easy"},
)

@dataclass(frozen=True)
class TriviaGame:
    name: str = "trivia"; command: str = "trivia"; description: str = "Answer a local trivia question."
    def question(self, category=None, chooser=None):
        options = [q for q in QUESTIONS if not category or q["category"] == category]
        if not options: raise ValueError("No trivia questions in that category")
        return (chooser or random.choice)(options)
    @staticmethod
    def answer(question, choice): return choice == question["answer"]
