from datetime import datetime, timezone
from app.database.collections import ECONOMY_BETS
from app.database.repositories.base import BaseRepository


class BetRepository(BaseRepository):
    def __init__(self, database): super().__init__(database, ECONOMY_BETS)
    async def create(self, chat_id, match_id, user_id, amount):
        now = datetime.now(timezone.utc)
        await self.insert_one({"chat_id": chat_id, "match_id": match_id,
            "user_id": user_id, "amount": amount, "status": "escrowed",
            "created_at": now, "updated_at": now})
    async def claim_match(self, match_id, settlement_id):
        await self.collection.update_many(
            {"match_id": match_id, "status": "escrowed"},
            {"$set": {"status": "processing", "settlement_id": settlement_id,
                       "updated_at": datetime.now(timezone.utc)}},
        )
        return await self.collection.find(
            {"match_id": match_id, "status": "processing", "settlement_id": settlement_id}
        ).to_list(length=2)
    async def mark_settled(self, settlement_id, status):
        await self.collection.update_many(
            {"settlement_id": settlement_id, "status": "processing"},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
        )
    async def release(self, settlement_id):
        await self.collection.update_many(
            {"settlement_id": settlement_id, "status": "processing"},
            {"$set": {"status": "escrowed", "updated_at": datetime.now(timezone.utc)},
             "$unset": {"settlement_id": ""}},
        )
    async def unsettled(self):
        return await self.collection.find(
            {"status": {"$in": ["escrowed", "processing"]}}
        ).to_list(length=None)
    async def reset_processing(self):
        await self.collection.update_many(
            {"status": "processing"},
            {"$set": {"status": "escrowed", "updated_at": datetime.now(timezone.utc)},
             "$unset": {"settlement_id": ""}},
        )
