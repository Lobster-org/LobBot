from app.database.repositories.module import (
    ModuleRepository,
)


class ModuleService:

    def __init__(self, database):

        self.repository = ModuleRepository(
            database
        )

    async def get_enabled_modules(
        self,
        group_id: int,
    ) -> list[str]:

        return await self.repository.get_enabled_modules(
            group_id
        )

    async def is_enabled(
        self,
        group_id: int,
        module_name: str,
    ) -> bool:

        enabled_modules = (
            await self.get_enabled_modules(
                group_id
            )
        )

        return module_name in enabled_modules
    
    async def enable_module(
        self,
        group_id: int,
        module_name: str,
    ):

        await self.repository.enable_module(
            group_id,
            module_name,
        )

    async def disable_module(
        self,
        group_id: int,
        module_name: str,
    ):

        await self.repository.disable_module(
            group_id,
            module_name,
        )