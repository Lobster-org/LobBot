from datetime import datetime, timezone

from app.database.collections import GROUPS
from app.database.repositories.base import BaseRepository


class ModuleRepository(BaseRepository):

    def __init__(self, database):

        super().__init__(
            database,
            GROUPS,
        )

    async def get_enabled_modules(
        self,
        group_id: int,
    ) -> list[str]:

        group = await self.find_one(
            {
                "telegram_id": group_id
            }
        )

        if not group:
            return []

        return group.get(
            "enabled_modules",
            [],
        )

    async def enable_module(
        self,
        group_id: int,
        module_name: str,
    ):

        return await self.update_one(
            {
                "telegram_id": group_id
            },
            {
                "$addToSet": {
                    "enabled_modules": module_name
                }
            },
        )

    async def disable_module(
        self,
        group_id: int,
        module_name: str,
    ):

        return await self.update_one(
            {
                "telegram_id": group_id
            },
            {
                "$pull": {
                    "enabled_modules": module_name
                }
            },
        )

    async def set_enabled_modules(
        self,
        group_id: int,
        modules: list[str],
    ):

        await self.update_one(
            {
                "telegram_id": group_id
            },
            {
                "$set": {
                    "enabled_modules": modules
                }
            },
        )
