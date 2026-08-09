from app.modules.base import BaseModule

from app.modules.group.handler import router


class GroupModule(BaseModule):
    name = "group"
    version = "1.0.0"
    description = (
        "Handles Telegram group regisration and membership."
    )
    enabled_by_default = True
    core = True

    async def setup(self, dispatcher):
        dispatcher.include_router(router)