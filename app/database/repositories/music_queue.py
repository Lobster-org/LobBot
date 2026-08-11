from datetime import datetime, timezone

from app.database.collections import MUSIC_SESSIONS
from app.database.repositories.base import BaseRepository


class MongoQueueRepository(BaseRepository):

    def __init__(self, database):
        super().__init__(
            database,
            MUSIC_SESSIONS,
        )

    async def save(
        self,
        chat_id: int,
        current: dict | None,
        queue: list[dict],
    ):
        now = datetime.now(timezone.utc)

        await self.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "current": current,
                    "queue": queue,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "chat_id": chat_id,
                    "created_at": now,
                },
            },
            upsert=True,
        )

    async def delete(self, chat_id: int):
        await self.delete_one(
            {"chat_id": chat_id}
        )

    async def load_active(self) -> list[dict]:
        cursor = self.collection.find(
            {
                "$or": [
                    {"current": {"$ne": None}},
                    {"queue.0": {"$exists": True}},
                ]
            }
        )

        return await cursor.to_list(length=None)
