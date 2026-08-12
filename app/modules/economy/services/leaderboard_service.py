from app.modules.economy.config import LEADERBOARD_SIZE


class LeaderboardService:
    FIELDS = {"xp": "xp", "coins": "coins", "wins": "games_won"}
    def __init__(self, profiles): self.profiles = profiles
    async def get(self, chat_id, metric="xp", user_id=None):
        field = self.FIELDS.get(metric)
        if not field: raise ValueError("Leaderboard must be xp, coins, or wins")
        rows = await self.profiles.leaderboard(chat_id, field, LEADERBOARD_SIZE)
        rank = await self.profiles.rank(chat_id, user_id, field) if user_id else None
        return rows, rank
