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
        group, _ = await self.register_group(
            telegram_id=telegram_id,
            title=title,
            group_type=group_type,
        )

        return group

    async def register_group(
        self,
        telegram_id: int,
        title: str | None,
        group_type: str,
    ) -> tuple[dict, bool]:
        now = datetime.now(timezone.utc)
        result = await self.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    "title": title,
                    "type": group_type,
                    "last_seen": now,
                },
                "$setOnInsert": {
                    "telegram_id": telegram_id,
                    "created_at": now,
                    "bot_status": "active",
                    "settings": {},
                    "enabled_modules": [],
                    "roles": {},
                    "permission_overrides": {},
                },
            },
            upsert=True,
        )
        group = await self.get_group(telegram_id)

        return group, result.upserted_id is not None

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

    async def get_custom_role(
        self,
        telegram_id: int,
        user_id: int,
    ) -> str | None:
        group = await self.get_group(
            telegram_id
        )

        if not group:
            return None

        return group.get("roles", {}).get(
            str(user_id)
        )

    async def set_custom_role(
        self,
        telegram_id: int,
        user_id: int,
        role: str,
    ):
        await self.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    f"roles.{user_id}": role
                }
            },
        )

    async def remove_custom_role(
        self,
        telegram_id: int,
        user_id: int,
    ):
        await self.update_one(
            {"telegram_id": telegram_id},
            {
                "$unset": {
                    f"roles.{user_id}": ""
                }
            },
        )

    async def get_permission_overrides(
        self,
        telegram_id: int,
        user_id: int,
    ) -> dict[str, bool]:
        group = await self.get_group(
            telegram_id
        )

        if not group:
            return {}

        overrides = group.get(
            "permission_overrides",
            {},
        ).get(str(user_id), {})

        if not isinstance(overrides, dict):
            return {}

        return {
            str(permission): bool(allowed)
            for permission, allowed in overrides.items()
        }

    async def set_permission_override(
        self,
        telegram_id: int,
        user_id: int,
        permission: str,
        allowed: bool,
    ):
        await self.update_one(
            {"telegram_id": telegram_id},
            {
                "$set": {
                    (
                        f"permission_overrides."
                        f"{user_id}.{permission}"
                    ): allowed
                }
            },
        )

    async def remove_permission_override(
        self,
        telegram_id: int,
        user_id: int,
        permission: str,
    ):
        await self.update_one(
            {"telegram_id": telegram_id},
            {
                "$unset": {
                    (
                        f"permission_overrides."
                        f"{user_id}.{permission}"
                    ): ""
                }
            },
        )
