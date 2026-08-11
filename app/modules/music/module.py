import logging

from app.modules.base import BaseModule
from app.modules.music.config import MUSIC_STORAGE_PATH
from app.modules.music.handler import router
from app.modules.music.services.playback_service import PlaybackService
from app.modules.music.state import music_state
from app.telegram.voice.events import VoiceEventHandler


logger = logging.getLogger(__name__)


class MusicModule(BaseModule):
    name = "music"
    version = "0.1.0"
    description = "Music search and Telegram voice streaming."
    enabled_by_default = False
    core = False

    async def setup(self, container, dispatcher):
        dispatcher.include_router(router)

    async def startup(self, container):
        if container.database is None:
            raise RuntimeError("Music requires an active database")
        if container.voice_service is None:
            raise RuntimeError("Music requires the voice service")
        if container.voice_lifecycle is None:
            raise RuntimeError("Music requires the voice lifecycle")

        music_state.configure(
            container.database,
            str(MUSIC_STORAGE_PATH),
            container.event_bus,
        )
        await music_state.queues.restore()

        music_state.player = PlaybackService(
            queue_service=music_state.queues,
            voice_service=container.voice_service,
            music_service=music_state.music_service,
            events=container.event_bus,
        )
        music_state.voice_events = VoiceEventHandler(
            voice_calls=container.voice_lifecycle.calls,
            playback_service=music_state.player,
        )
        music_state.voice_events.register()
        await music_state.player.restore()
        logger.info("Music runtime ready")

    async def shutdown(self, container):
        if music_state.player:
            await music_state.player.shutdown()

        if music_state.music_service:
            await music_state.music_service.shutdown()

        music_state.reset()
        logger.info("Music runtime stopped")
