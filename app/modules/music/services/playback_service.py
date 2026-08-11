import asyncio
import logging

from app.modules.music.events import (
    PLAYBACK_STOPPED,
    TRACK_FINISHED,
    TRACK_SKIPPED,
    TRACK_STARTED,
)


logger = logging.getLogger(__name__)


class PlaybackService:

    _LOCK_STRIPES = 64

    def __init__(
        self,
        queue_service,
        voice_service,
        music_service=None,
        events=None,
    ):
        self.queue_service = queue_service
        self.voice_service = voice_service
        self.music_service = music_service
        self.events = events
        self.tasks: dict[int, asyncio.Task] = {}
        self._operation_locks = [
            asyncio.Lock()
            for _ in range(self._LOCK_STRIPES)
        ]

    def _operation_lock(
        self,
        chat_id: int,
    ) -> asyncio.Lock:
        return self._operation_locks[
            hash(chat_id) % self._LOCK_STRIPES
        ]

    async def ensure_playing(
        self,
        chat_id: int,
    ):
        async with self._operation_lock(chat_id):
            queue = self.queue_service.get(chat_id)

            if queue.is_playing or not queue.items:
                return

            task = self.tasks.get(chat_id)
            if task and not task.done():
                return

            self.tasks[chat_id] = asyncio.create_task(
                self._run_player(chat_id)
            )

    async def restore(self):
        chat_ids = self.queue_service.active_chat_ids()

        for chat_id in chat_ids:
            await self.ensure_playing(chat_id)

        logger.info(
            "Scheduled restored music sessions: count=%s",
            len(chat_ids),
        )

    async def shutdown(self):
        """Cancel owned tasks and leave calls without deleting queues."""
        tasks = list(self.tasks.values())

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        self.tasks.clear()

        chat_ids = self.queue_service.active_chat_ids()
        results = await asyncio.gather(
            *(
                self.voice_service.stop(chat_id)
                for chat_id in chat_ids
            ),
            return_exceptions=True,
        )

        for chat_id, result in zip(chat_ids, results):
            if isinstance(result, Exception):
                logger.error(
                    "Failed to leave voice call during shutdown: "
                    "chat=%s error=%r",
                    chat_id,
                    result,
                )

        logger.info(
            "Playback service stopped: tasks=%s calls=%s",
            len(tasks),
            len(chat_ids),
        )

    async def _run_player(
        self,
        chat_id: int,
    ):
        queue = self.queue_service.get(chat_id)

        started = None

        try:
            async with self._operation_lock(chat_id):
                started = await self._play_next(
                    chat_id
                )
        except asyncio.CancelledError:
            queue.is_playing = False
            raise
        except Exception:
            logger.exception(
                "Playback task failed: chat=%s",
                chat_id,
            )
            queue.is_playing = False
        finally:
            self.tasks.pop(chat_id, None)

        if started:
            await self._emit_track_event(
                TRACK_STARTED,
                chat_id,
                started,
            )

    async def _play_next(
        self,
        chat_id: int,
    ):
        queue = self.queue_service.get(chat_id)

        while True:
            item = await self.queue_service.next(chat_id)

            if not item:
                queue.is_playing = False
                queue.is_paused = False
                logger.info(
                    "Queue finished: chat=%s",
                    chat_id,
                )
                return None

            track = item.track

            if not track.file_path:
                logger.error(
                    "Skipping track without file path: chat=%s title=%s",
                    chat_id,
                    track.title,
                )
                continue

            queue.is_playing = True
            queue.is_paused = False

            logger.info(
                "Starting track: chat=%s title=%s",
                chat_id,
                track.title,
            )

            try:
                await self.voice_service.play(
                    chat_id,
                    track.file_path,
                )
            except FileNotFoundError:
                logger.exception(
                    "Audio file disappeared; skipping track: "
                    "chat=%s title=%s path=%s",
                    chat_id,
                    track.title,
                    track.file_path,
                )
                continue
            except Exception:
                logger.exception(
                    "Voice playback failed; preserving track for retry: "
                    "chat=%s title=%s",
                    chat_id,
                    track.title,
                )
                await self.queue_service.requeue_current(
                    chat_id
                )
                return None

            if self.music_service:
                try:
                    await self.music_service.mark_used(track)
                except Exception:
                    logger.exception(
                        "Failed to update cache usage: source=%s source_id=%s",
                        track.source,
                        track.source_id,
                    )

            return item

    async def handle_stream_end(
        self,
        chat_id: int,
    ):
        finished = None
        started = None

        async with self._operation_lock(chat_id):
            queue = self.queue_service.get(chat_id)

            logger.info(
                "Stream ended: chat=%s",
                chat_id,
            )

            finished = await (
                self.queue_service.remove_current(
                    chat_id
                )
            )

            if not finished:
                logger.warning(
                    "Stream ended without an active track: chat=%s",
                    chat_id,
                )
                return

            if not queue.items:
                await self.queue_service.clear(chat_id)
                logger.info(
                    "No more tracks: chat=%s",
                    chat_id,
                )
            else:
                started = await self._play_next(
                    chat_id
                )

        await self._emit_track_event(
            TRACK_FINISHED,
            chat_id,
            finished,
        )

        if started:
            await self._emit_track_event(
                TRACK_STARTED,
                chat_id,
                started,
            )

    async def pause(
        self,
        chat_id: int,
    ) -> bool:
        async with self._operation_lock(chat_id):
            queue = self.queue_service.get(chat_id)

            if (
                not queue.is_playing
                or not queue.current
                or queue.is_paused
            ):
                return False

            await self.voice_service.pause(chat_id)
            queue.is_paused = True

            return True

    async def resume(
        self,
        chat_id: int,
    ) -> bool:
        async with self._operation_lock(chat_id):
            queue = self.queue_service.get(chat_id)

            if (
                not queue.is_playing
                or not queue.current
                or not queue.is_paused
            ):
                return False

            await self.voice_service.resume(chat_id)
            queue.is_paused = False

            return True

    async def skip(
        self,
        chat_id: int,
    ):
        skipped = None
        started = None

        async with self._operation_lock(chat_id):
            queue = self.queue_service.get(chat_id)

            if not queue.current:
                return None

            skipped = await (
                self.queue_service.remove_current(
                    chat_id
                )
            )

            if queue.items:
                started = await self._play_next(
                    chat_id
                )
            else:
                await self.queue_service.clear(chat_id)

                try:
                    await self.voice_service.stop(chat_id)
                except Exception:
                    logger.exception(
                        "Failed to stop skipped voice stream: chat=%s",
                        chat_id,
                    )

        await self._emit_track_event(
            TRACK_SKIPPED,
            chat_id,
            skipped,
        )

        if started:
            await self._emit_track_event(
                TRACK_STARTED,
                chat_id,
                started,
            )

        return skipped

    async def stop(
        self,
        chat_id: int,
    ) -> bool:
        current = None
        queued_count = 0

        async with self._operation_lock(chat_id):
            queue = self.queue_service.get(chat_id)
            had_playback = bool(
                queue.current
                or queue.items
                or queue.is_playing
            )

            if not had_playback:
                return False

            current = queue.current
            queued_count = len(queue.items)

            await self.queue_service.clear(chat_id)

            try:
                await self.voice_service.stop(chat_id)
            except Exception:
                logger.exception(
                    "Failed to stop voice chat: chat=%s",
                    chat_id,
                )

        if self.events:
            await self.events.emit(
                PLAYBACK_STOPPED,
                {
                    "chat_id": chat_id,
                    "track": (
                        current.track
                        if current
                        else None
                    ),
                    "requested_by": (
                        current.requested_by
                        if current
                        else None
                    ),
                    "queued_count": queued_count,
                },
            )

        return True

    async def _emit_track_event(
        self,
        event_name: str,
        chat_id: int,
        item,
    ):
        if not self.events or not item:
            return

        await self.events.emit(
            event_name,
            {
                "chat_id": chat_id,
                "track": item.track,
                "requested_by": item.requested_by,
            },
        )
