from app.modules.base import BaseModule
from app.modules.music.handler import router

class MusicModule(BaseModule):

    name = "music"
    version = "0.1.0"
    description = (
        "Music search and Telegram voice streaming."
    )
    enabled_by_default = False
    core = False

    async def setup(self, dispatcher):
        dispatcher.include_router(
            router
        )
