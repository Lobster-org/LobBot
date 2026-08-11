from app.database.repositories.module import (
    ModuleRepository,
)

from app.core.event_names import (
    MODULE_DISABLED,
    MODULE_ENABLED,
)
from app.core.events import event_bus


class ModuleService:

    def __init__(
        self,
        database=None,
        repository=None,
        events=event_bus,
    ):

        self.repository = (
            repository
            or ModuleRepository(database)
        )
        self.events = events

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
        changed_by: int | None = None,
    ) -> bool:

        result = await self.repository.enable_module(
            group_id,
            module_name,
        )

        changed = result.modified_count > 0

        if changed:
            await self.events.emit(
                MODULE_ENABLED,
                {
                    "chat_id": group_id,
                    "module_name": module_name,
                    "changed_by": changed_by,
                },
            )

        return changed

    async def disable_module(
        self,
        group_id: int,
        module_name: str,
        changed_by: int | None = None,
    ) -> bool:

        result = await self.repository.disable_module(
            group_id,
            module_name,
        )

        changed = result.modified_count > 0

        if changed:
            await self.events.emit(
                MODULE_DISABLED,
                {
                    "chat_id": group_id,
                    "module_name": module_name,
                    "changed_by": changed_by,
                },
            )

        return changed
