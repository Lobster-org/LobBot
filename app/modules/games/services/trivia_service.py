import logging
import random
from html import unescape

import aiohttp


logger = logging.getLogger(__name__)

TRIVIA_CATEGORIES = {
    "any": (None, "Any Category"),
    "general": (9, "General Knowledge"),
    "books": (10, "Books"),
    "film": (11, "Film"),
    "music": (12, "Music"),
    "science": (17, "Science & Nature"),
    "computers": (18, "Computers"),
    "sports": (21, "Sports"),
    "geography": (22, "Geography"),
    "history": (23, "History"),
}


class TriviaService:
    API_URL = "https://opentdb.com/api.php"

    def __init__(self, fallback, randomizer=None, timeout_seconds=8):
        self.fallback = fallback
        self.randomizer = randomizer or random
        self.timeout_seconds = timeout_seconds

    async def questions(self, amount: int, category: str = "any") -> list[dict]:
        if category not in TRIVIA_CATEGORIES:
            raise ValueError("Unknown trivia category")
        category_id = TRIVIA_CATEGORIES[category][0]
        params = {"amount": amount, "type": "multiple"}
        if category_id is not None:
            params["category"] = category_id
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.API_URL, params=params) as response:
                    response.raise_for_status()
                    payload = await response.json()
            if payload.get("response_code") != 0 or len(payload.get("results", ())) < amount:
                raise RuntimeError(f"Trivia API response code {payload.get('response_code')}")
            return [self._normalize(item) for item in payload["results"]]
        except Exception:
            logger.warning(
                "Trivia API unavailable; using local fallback: category=%s amount=%s",
                category, amount, exc_info=True,
            )
            return self._fallback_questions(amount, category)

    def _normalize(self, item):
        correct = unescape(item["correct_answer"])
        choices = [unescape(value) for value in item["incorrect_answers"]] + [correct]
        self.randomizer.shuffle(choices)
        return {"question": unescape(item["question"]), "choices": tuple(choices),
                "answer": choices.index(correct), "category": unescape(item["category"]),
                "difficulty": item.get("difficulty", "unknown")}

    def _fallback_questions(self, amount, category):
        pool = list(self.fallback)
        if category not in {"any", "general"}:
            aliases = {"computers": "technology", "books": "literature"}
            filtered = [q for q in pool if q["category"] == aliases.get(category, category)]
            if filtered: pool = filtered
        questions = []
        while len(questions) < amount:
            cycle = pool.copy(); self.randomizer.shuffle(cycle)
            questions.extend(dict(question) for question in cycle)
        return questions[:amount]
