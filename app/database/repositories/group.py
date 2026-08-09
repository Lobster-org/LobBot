from datetime import datetime, timezone

from app.database.collections import GROUPS
from app.database.models.group import (
    create_group_document,
)
from app.database.repositories.base import (
    BaseRepository,
)


class GroupRepository(BaseRepository):

    def __init__(self, database):
        super().__init__(
            database,
            GROUPS,
        )

    async def get_group(
        self,
        telegram_id: int,
    ):
        return await self.find_one(
            {
                "telegram_id": telegram_id
            }
        )

    async def create_group(
        self,
        telegram_id: int,
        title: str | None,
        group_type: str,
    ):
        document = create_group_document(
            telegram_id=telegram_id,
            title=title,
            group_type=group_type,
        )

        await self.insert_one(document)

        return await self.get_group(
            telegram_id
        )

    async def get_or_create_group(
        self,
        telegram_id: int,
        title: str | None,
        group_type: str,
    ):
        group = await self.get_group(
            telegram_id
        )

        if group:

            await self.update_group_activity(
                telegram_id=telegram_id,
                title=title,
            )

            return await self.get_group(
                telegram_id
            )

        return await self.create_group(
            telegram_id=telegram_id,
            title=title,
            group_type=group_type,
        )

    async def update_group_activity(
        self,
        telegram_id: int,
        title: str | None = None,
    ):
        now = datetime.now(timezone.utc)

        updates = {
            "last_seen": now,
        }

        if title is not None:
            updates["title"] = title

        await self.update_one(
            {
                "telegram_id": telegram_id
            },
            {
                "$set": updates
            },
        )
        
    async def update_bot_status(
        self,
        telegram_id: int,
        status: str,
    ):
        await self.update_one(
            {
                "telegram_id": telegram_id
            },
            {
                "$set": {
                    "bot_status": status
                }
            },
        )
    
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

    async def update_group(
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

        return await self.get_group(
            telegram_id
        )