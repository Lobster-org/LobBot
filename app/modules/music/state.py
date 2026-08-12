from app.database.repositories.music_queue import MongoQueueRepository
from app.modules.music.services.music_service import MusicService
from app.modules.music.services.queue_service import QueueService
from app.modules.music.services.search_session import SearchSessionManager


class MusicState:
    """Module-local references used by thin Telegram handlers."""

    def __init__(self):
        self.search_sessions = SearchSessionManager(ttl=120)
        self.queues = QueueService()
        self.music_service = None
        self.player = None
        self.voice_events = None
        self.voice_membership = None

    def configure(
        self,
        database,
        storage_path: str,
        events,
    ):
        self.queues = QueueService(
            MongoQueueRepository(database),
            events=events,
        )
        self.music_service = MusicService(database, storage_path)

    def reset(self):
        self.search_sessions = SearchSessionManager(ttl=120)
        self.queues = QueueService()
        self.music_service = None
        self.player = None
        self.voice_events = None
        self.voice_membership = None


music_state = MusicState()
