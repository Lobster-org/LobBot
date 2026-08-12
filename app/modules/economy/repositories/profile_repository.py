from datetime import datetime, timezone
from pymongo import ReturnDocument

from app.database.collections import ECONOMY_PROFILES, ECONOMY_SETTINGS
from app.database.repositories.base import BaseRepository
from app.modules.economy.models.profile import EconomyProfile


class ProfileRepository(BaseRepository):
    def __init__(self, database): super().__init__(database, ECONOMY_PROFILES)

    async def get(self, chat_id, user_id):
        await self.ensure(chat_id, user_id)
        doc = await self.find_one({"chat_id": chat_id, "user_id": user_id})
        return EconomyProfile.from_document(chat_id, user_id, doc)

    async def ensure(self, chat_id, user_id):
        now = datetime.now(timezone.utc)
        await self.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$setOnInsert": {"chat_id": chat_id, "user_id": user_id, "xp": 0,
                "level": 0, "coins": 0, "daily_streak": 0, "games_played": 0,
                "games_won": 0, "achievements": [], "created_at": now,
                "updated_at": now}}, upsert=True,
        )

    async def increment(self, chat_id, user_id, increments):
        now = datetime.now(timezone.utc)
        defaults = {"xp": 0, "level": 0, "coins": 0, "daily_streak": 0,
                    "games_played": 0, "games_won": 0}
        for field in increments: defaults.pop(field, None)
        return await self.collection.find_one_and_update(
            {"chat_id": chat_id, "user_id": user_id},
            {"$inc": increments, "$set": {"updated_at": now}, "$setOnInsert": {
                "chat_id": chat_id, "user_id": user_id, **defaults,
                "achievements": [], "created_at": now,
            }}, upsert=True, return_document=ReturnDocument.AFTER,
        )

    async def debit(self, chat_id, user_id, amount):
        return await self.collection.find_one_and_update(
            {"chat_id": chat_id, "user_id": user_id, "coins": {"$gte": amount}},
            {"$inc": {"coins": -amount}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )

    async def set_level(self, chat_id, user_id, level):
        result = await self.update_one({"chat_id": chat_id, "user_id": user_id}, {"$max": {"level": level}})
        return result.modified_count > 0

    async def unlock(self, chat_id, user_id, achievement_id):
        result = await self.update_one(
            {"chat_id": chat_id, "user_id": user_id, "achievements": {"$ne": achievement_id}},
            {"$addToSet": {"achievements": achievement_id}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0

    async def leaderboard(self, chat_id, field, limit):
        return await self.collection.find({"chat_id": chat_id}).sort(field, -1).limit(limit).to_list(length=limit)

    async def rank(self, chat_id, user_id, field):
        profile = await self.find_one({"chat_id": chat_id, "user_id": user_id})
        if not profile: return None
        return await self.collection.count_documents({"chat_id": chat_id, field: {"$gt": profile.get(field, 0)}}) + 1

    async def claim_daily(self, chat_id, user_id, now, cutoff, streak):
        query = {"chat_id": chat_id, "user_id": user_id,
                 "$or": [{"last_daily_at": {"$lte": cutoff}}, {"last_daily_at": {"$exists": False}}]}
        return await self.collection.find_one_and_update(
            query, {"$set": {"last_daily_at": now, "daily_streak": streak, "updated_at": now},
                    "$setOnInsert": {"chat_id": chat_id, "user_id": user_id, "xp": 0, "level": 0, "coins": 0,
                                     "games_played": 0, "games_won": 0, "achievements": [], "created_at": now}},
            return_document=ReturnDocument.AFTER,
        )


class EconomySettingsRepository(BaseRepository):
    def __init__(self, database): super().__init__(database, ECONOMY_SETTINGS)
    async def get(self, chat_id):
        doc = await self.find_one({"chat_id": chat_id}) or {}
        return {"rewards_enabled": doc.get("rewards_enabled", True), "xp_multiplier": float(doc.get("xp_multiplier", 1.0)),
                "coin_multiplier": float(doc.get("coin_multiplier", 1.0)), "daily_enabled": doc.get("daily_enabled", True)}
    async def save(self, chat_id, **settings):
        allowed = {key: value for key, value in settings.items() if key in {"rewards_enabled", "xp_multiplier", "coin_multiplier", "daily_enabled"}}
        if not allowed: return False
        allowed["updated_at"] = datetime.now(timezone.utc)
        result = await self.update_one({"chat_id": chat_id}, {"$set": allowed, "$setOnInsert": {"chat_id": chat_id, "created_at": allowed["updated_at"]}}, upsert=True)
        return result.modified_count > 0 or result.upserted_id is not None
