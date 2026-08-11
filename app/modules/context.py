from app.core.container import container
from app.services.module_service import (
    ModuleService,
)


async def is_module_enabled(group_id: int, module_name: str) -> bool:

    database = container.database

    if database is None:
        raise RuntimeError(
            "Module context used before application startup"
        )

    service = ModuleService(
        database
    )

    enabled_modules = (
        await service.get_enabled_modules(
            group_id
        )
    )

    return module_name in enabled_modules
