import re
from datetime import datetime, timezone

from app.database.collections import USERS
from app.database.models.user import (
    create_user_document,
)
from app.database.repositories.base import (
    BaseRepository,
)


class UserRepository(BaseRepository):

    def __init__(self, database):
        super().__init__(
            database,
            USERS,
        )

    async def get_user(
        self,
        telegram_id: int,
    ):
        return await self.find_one(
            {
                "telegram_id": telegram_id
            }
        )

    async def get_user_by_username(
        self,
        username: str,
    ):
        normalized = username.lstrip("@")

        if not normalized:
            return None

        return await self.find_one(
            {
                "username": {
                    "$regex": f"^{re.escape(normalized)}$",
                    "$options": "i",
                }
            }
        )

    async def create_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None = None,
    ):
        document = create_user_document(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

        result = await self.insert_one(
            document
        )

        return await self.get_user(
            telegram_id
        )

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None = None,
    ):
        user, _ = await self.register_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

        return user

    async def register_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None = None,
    ) -> tuple[dict, bool]:
        now = datetime.now(timezone.utc)
        result = await self.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "last_seen": now,
                },
                "$setOnInsert": {
                    "telegram_id": telegram_id,
                    "created_at": now,
                    "preferences": {},
                },
            },
            upsert=True,
        )
        user = await self.get_user(telegram_id)

        return user, result.upserted_id is not None

    async def update_last_seen(
        self,
        telegram_id: int,
    ):
        now = datetime.now(timezone.utc)

        await self.update_one(
            {
                "telegram_id": telegram_id
            },
            {
                "$set": {
                    "last_seen": now
                }
            },
        )

    async def update_user(
        self,
        telegram_id: int,
        updates: dict,
    ):
        await self.update_one(
            {
                "telegram_id": telegram_id
            },
            {
                "$set": updates
            },
        )

        return await self.get_user(
            telegram_id
        )
