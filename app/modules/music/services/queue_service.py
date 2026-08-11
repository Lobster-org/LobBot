import asyncio
import logging
from copy import deepcopy
from datetime import datetime, timezone

from app.modules.music.models.queue import MusicQueue, QueueItem
from app.modules.music.models.track import Track
from app.modules.music.events import TRACK_QUEUED


logger = logging.getLogger(__name__)


class QueueService:

    _LOCK_STRIPES = 64

    def __init__(
        self,
        repository=None,
        events=None,
    ):
        self.repository = repository
        self.events = events
        self._queues: dict[int, MusicQueue] = {}
        self._locks = [
            asyncio.Lock()
            for _ in range(self._LOCK_STRIPES)
        ]

    def get(self, chat_id: int) -> MusicQueue:
        if chat_id not in self._queues:
            self._queues[chat_id] = MusicQueue(
                chat_id=chat_id
            )

        return self._queues[chat_id]

    def get_lock(self, chat_id: int) -> asyncio.Lock:
        return self._locks[
            hash(chat_id) % self._LOCK_STRIPES
        ]

    async def add(
        self,
        chat_id: int,
        item: QueueItem,
    ) -> int:
        async with self.get_lock(chat_id):
            queue = self.get(chat_id)
            previous = deepcopy(queue)
            position = queue.add(item)

            try:
                await self._persist(queue)
            except Exception:
                self._queues[chat_id] = previous
                raise

        if self.events:
            await self.events.emit(
                TRACK_QUEUED,
                {
                    "chat_id": chat_id,
                    "track": item.track,
                    "requested_by": item.requested_by,
                    "position": position,
                },
            )

        return position

    async def next(
        self,
        chat_id: int,
    ) -> QueueItem | None:
        async with self.get_lock(chat_id):
            queue = self.get(chat_id)
            previous = deepcopy(queue)
            item = queue.next()

            try:
                await self._persist(queue)
            except Exception:
                self._queues[chat_id] = previous
                raise

            return item

    async def remove(
        self,
        chat_id: int,
        index: int,
    ) -> QueueItem | None:
        async with self.get_lock(chat_id):
            queue = self.get(chat_id)
            previous = deepcopy(queue)
            item = queue.remove(index)

            if item is None:
                return None

            try:
                await self._persist(queue)
            except Exception:
                self._queues[chat_id] = previous
                raise

            return item

    async def clear(self, chat_id: int):
        async with self.get_lock(chat_id):
            queue = self.get(chat_id)
            previous = deepcopy(queue)
            queue.clear()

            try:
                await self._persist(queue)
            except Exception:
                self._queues[chat_id] = previous
                raise

            self._queues.pop(chat_id, None)

    async def requeue_current(self, chat_id: int):
        async with self.get_lock(chat_id):
            queue = self.get(chat_id)

            if not queue.current:
                return

            previous = deepcopy(queue)
            queue.items.insert(0, queue.current)
            queue.current = None
            queue.is_playing = False
            queue.is_paused = False

            try:
                await self._persist(queue)
            except Exception:
                self._queues[chat_id] = previous
                raise

    async def remove_current(
        self,
        chat_id: int,
    ) -> QueueItem | None:
        async with self.get_lock(chat_id):
            queue = self.get(chat_id)

            if not queue.current:
                return None

            previous = deepcopy(queue)
            item = queue.current
            queue.current = None
            queue.is_paused = False

            try:
                await self._persist(queue)
            except Exception:
                self._queues[chat_id] = previous
                raise

            return item

    async def save(self, chat_id: int):
        async with self.get_lock(chat_id):
            await self._persist(
                self.get(chat_id)
            )

    async def restore(self) -> list[int]:
        if not self.repository:
            return []

        documents = await self.repository.load_active()
        restored = []

        for document in documents:
            chat_id = None

            try:
                chat_id = int(document["chat_id"])
                items = []

                current = document.get("current")
                if current:
                    items.append(
                        self._deserialize_item(current)
                    )

                items.extend(
                    self._deserialize_item(item)
                    for item in document.get("queue", [])
                )

                if not items:
                    continue

                self._queues[chat_id] = MusicQueue(
                    chat_id=chat_id,
                    items=items,
                )

                await self._persist(
                    self._queues[chat_id]
                )

                restored.append(chat_id)
            except Exception:
                if chat_id is not None:
                    self._queues.pop(chat_id, None)
                logger.exception(
                    "Failed to restore music session: document=%r",
                    document,
                )

        logger.info(
            "Restored music sessions: count=%s",
            len(restored),
        )

        return restored

    def snapshot(self, chat_id: int) -> MusicQueue:
        return deepcopy(
            self.get(chat_id)
        )

    def active_chat_ids(self) -> list[int]:
        return [
            chat_id
            for chat_id, queue in self._queues.items()
            if queue.current or queue.items
        ]

    async def _persist(self, queue: MusicQueue):
        if not self.repository:
            return

        if not queue.current and not queue.items:
            await self.repository.delete(
                queue.chat_id
            )
            return

        await self.repository.save(
            chat_id=queue.chat_id,
            current=(
                self._serialize_item(queue.current)
                if queue.current
                else None
            ),
            queue=[
                self._serialize_item(item)
                for item in queue.items
            ],
        )

    @staticmethod
    def _serialize_item(item: QueueItem) -> dict:
        track = item.track

        return {
            "source": track.source,
            "source_id": track.source_id,
            "title": track.title,
            "artist": track.artist,
            "duration": track.duration,
            "url": track.url,
            "thumbnail": track.thumbnail,
            "file_path": track.file_path,
            "requested_by": item.requested_by,
            "requested_at": item.requested_at,
        }

    @staticmethod
    def _deserialize_item(document: dict) -> QueueItem:
        requested_at = document.get("requested_at")

        if not isinstance(requested_at, datetime):
            requested_at = datetime.now(timezone.utc)

        return QueueItem(
            track=Track(
                title=document.get("title") or "Unknown",
                artist=document.get("artist"),
                duration=document.get("duration"),
                url=document.get("url"),
                thumbnail=document.get("thumbnail"),
                source=document.get("source"),
                source_id=document.get("source_id"),
                file_path=document.get("file_path"),
            ),
            requested_by=int(
                document.get("requested_by", 0)
            ),
            requested_at=requested_at,
        )
