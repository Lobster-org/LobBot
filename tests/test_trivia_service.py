import pytest

from app.modules.games.games.trivia import QUESTIONS
from app.modules.games.services.trivia_service import TriviaService


class Randomizer:
    def shuffle(self, values): values.reverse()


def test_api_question_normalization_decodes_and_randomizes_choices():
    service = TriviaService(QUESTIONS, Randomizer())
    question = service._normalize({
        "question": "Tom &amp; Jerry?", "correct_answer": "Yes",
        "incorrect_answers": ["No", "Maybe", "Unknown"],
        "category": "Entertainment: Cartoon &amp; Animations", "difficulty": "easy",
    })
    assert question["question"] == "Tom & Jerry?"
    assert question["choices"] == ("Yes", "Unknown", "Maybe", "No")
    assert question["answer"] == 0


def test_fallback_produces_requested_round_count():
    service = TriviaService(QUESTIONS, Randomizer())
    questions = service._fallback_questions(20, "any")
    assert len(questions) == 20
    assert all("question" in item and len(item["choices"]) == 4 for item in questions)


@pytest.mark.asyncio
async def test_unknown_category_is_rejected_before_network_call():
    service = TriviaService(QUESTIONS)
    with pytest.raises(ValueError):
        await service.questions(5, "unknown")
