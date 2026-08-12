import logging
from app.modules.economy.events import ACHIEVEMENT_UNLOCKED
from app.modules.economy.models.achievement import Achievement

logger = logging.getLogger(__name__)

ACHIEVEMENTS = {
    "first_game": Achievement("first_game", "Game On", "Complete your first game."),
    "first_win": Achievement("first_win", "Winner Winner", "Win your first game."),
    "ten_wins": Achievement("ten_wins", "Double Digits", "Win ten games."),
    "level_5": Achievement("level_5", "High Five", "Reach level 5."),
    "level_10": Achievement("level_10", "Perfect Ten", "Reach level 10."),
    "coin_1000": Achievement("coin_1000", "Tiny Treasury", "Hold 1,000 coins."),
    "daily_streak_7": Achievement("daily_streak_7", "Week Warrior", "Reach a seven-day daily streak."),
}


class AchievementService:
    def __init__(self, profiles, events): self.profiles, self.events = profiles, events
    async def evaluate(self, chat_id, user_id):
        p = await self.profiles.get(chat_id, user_id)
        eligible = {"first_game": p.games_played >= 1, "first_win": p.games_won >= 1,
                    "ten_wins": p.games_won >= 10, "level_5": p.level >= 5,
                    "level_10": p.level >= 10, "coin_1000": p.coins >= 1000,
                    "daily_streak_7": p.daily_streak >= 7}
        unlocked = []
        for achievement_id, condition in eligible.items():
            if condition and await self.profiles.unlock(chat_id, user_id, achievement_id):
                unlocked.append(ACHIEVEMENTS[achievement_id]); logger.info("Achievement unlocked: chat=%s user=%s achievement=%s", chat_id, user_id, achievement_id)
                await self.events.emit(ACHIEVEMENT_UNLOCKED, {"chat_id": chat_id, "user_id": user_id, "achievement": achievement_id})
        return unlocked
