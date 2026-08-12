from dataclasses import asdict
from datetime import datetime, timezone

from app.database.collections import ECONOMY_TRANSACTIONS
from app.database.repositories.base import BaseRepository


class TransactionRepository(BaseRepository):
    def __init__(self, database): super().__init__(database, ECONOMY_TRANSACTIONS)
    async def record(self, transaction):
        document = asdict(transaction); document["created_at"] = datetime.now(timezone.utc)
        return await self.insert_one(document)
