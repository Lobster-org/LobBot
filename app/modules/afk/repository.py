from datetime import datetime, timezone
import re

from pymongo import ReturnDocument


class AFKRepository:
    def __init__(self, database): self.collection = database["afk_states"]
    async def set(self, chat_id, user, status, reason):
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"chat_id": chat_id, "user_id": user.id},
            {"$set": {"status": status, "reason": reason, "started_at": now, "username": user.username,
                      "display_name": user.full_name, "updated_at": now, "mentions": []}}, upsert=True,
        )
        return await self.get(chat_id, user.id)
    async def get(self, chat_id, user_id): return await self.collection.find_one({"chat_id": chat_id, "user_id": user_id})
    async def find_username(self, chat_id, username): return await self.collection.find_one({"chat_id": chat_id, "username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}})
    async def clear(self, chat_id, user_id): return await self.collection.find_one_and_delete({"chat_id": chat_id, "user_id": user_id})
    async def add_mention(self, chat_id, user_id, mention):
        return await self.collection.find_one_and_update(
            {"chat_id": chat_id, "user_id": user_id},
            {"$push": {"mentions": {"$each": [mention], "$slice": -20}}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
