from app.modules.base import BaseModule
from app.modules.management.handler import router


class ManagementModule(BaseModule):

    name = "management"
    version = "1.0.0"
    description = (
        "Manage LobBot modules and group features."
    )
    enabled_by_default = True
    core = True

    async def setup(self, container, dispatcher):

        dispatcher.include_router(
            router
        )
