from app.modules.music.services.queue_service import (
    QueueService
)

from app.modules.music.services.search_session import (
    SearchSessionManager,
)

from app.database.repositories.music_queue import (
    MongoQueueRepository,
)

from app.modules.music.services.music_service import (
    MusicService,
)

from app.core.events import event_bus


class MusicState:

    def __init__(self):
        self.search_sessions = (
            SearchSessionManager(
                ttl=120
            )
        )

        self.queues = QueueService()

        self.music_service = None

        # One playback coordinator manages all per-chat queues.
        # It is initialized after the voice client starts.
        self.player = None

        self.voice_events = None

    def configure(
        self,
        database,
        storage_path: str,
    ):
        self.queues = QueueService(
            MongoQueueRepository(database),
            events=event_bus,
        )
        self.music_service = MusicService(
            database,
            storage_path,
        )


music_state = MusicState()
