from app.database.mongodb import mongodb
from app.services.module_service import (
    ModuleService,
)


async def is_module_enabled(group_id: int, module_name: str) -> bool:

    database = mongodb.get_database()

    service = ModuleService(
        database
    )

    enabled_modules = (
        await service.get_enabled_modules(
            group_id
        )
    )

    return module_name in enabled_modules