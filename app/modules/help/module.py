from app.modules.base import BaseModule
from app.modules.help.handler import router


class HelpModule(BaseModule):
    name = "help"
    version = "1.0.0"
    description = "Provides command discovery and help navigation"
    enabled_by_default = True
    core = True

    async def setup(self, container, dispatcher):
        dispatcher.include_router(router)
