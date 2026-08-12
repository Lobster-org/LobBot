from math import isqrt

from app.modules.economy.config import LEVEL_XP_CONSTANT
from app.modules.economy.events import LEVEL_UP, XP_GAINED


class XPService:
    """Levels follow floor(sqrt(xp / 100)); level 1 starts at 100 XP."""
    def __init__(self, profiles, events): self.profiles, self.events = profiles, events

    @staticmethod
    def calculate_level(xp):
        if xp < 0: raise ValueError("XP cannot be negative")
        return isqrt(xp // LEVEL_XP_CONSTANT)

    async def add_xp(self, chat_id, user_id, amount, reason):
        if amount <= 0: raise ValueError("XP amount must be positive")
        document = await self.profiles.increment(chat_id, user_id, {"xp": amount})
        new_xp = document["xp"]
        new_level = self.calculate_level(new_xp)
        old_level = document.get("level", 0)
        promoted = new_level > old_level and await self.profiles.set_level(chat_id, user_id, new_level)
        await self.events.emit(XP_GAINED, {"chat_id": chat_id, "user_id": user_id, "amount": amount, "reason": reason, "xp": new_xp})
        if promoted:
            await self.events.emit(LEVEL_UP, {"chat_id": chat_id, "user_id": user_id, "old_level": old_level, "new_level": new_level})
        return new_xp, new_level
