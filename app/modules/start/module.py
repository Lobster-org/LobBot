from app.modules.base import BaseModule

from app.modules.start.handler import router


class StartModule(BaseModule):
    name = "start"
    version = "1.0.0"
    description = (
        "Handles user registration and start command"
    )
    enabled_by_default = True
    core = True
    
    async def setup(self, container, dispatcher):

        dispatcher.include_router(router)
