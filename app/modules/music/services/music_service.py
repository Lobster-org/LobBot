import asyncio
import logging

from app.modules.music.cache.manager import (
    MusicCache,
)

from app.modules.music.models.track import Track

from app.modules.music.services.download_service import (
    DownloadService,
)

from app.modules.music.services.search_service import (
    SearchService,
)

from app.modules.music.providers.youtube import (
    YouTubeProvider,
)

from app.modules.music.services.cache_service import (
    MusicCacheService,
)


logger = logging.getLogger(__name__)

class MusicService:

    def __init__(
        self,
        database,
        storage_path: str,
    ):

        provider = YouTubeProvider()

        self.search_service = (
            SearchService(provider)
        )

        self.download_service = (
            DownloadService(
                provider,
                storage_path,
            )
        )

        self.cache = MusicCache(
            storage_path
        )

        self.cache_service = MusicCacheService(
            database,
            storage_path,
        )

        self._preparations: dict[
            tuple[str | None, str | None],
            asyncio.Task,
        ] = {}
        self._preparations_lock = asyncio.Lock()

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[Track]:

        return await (
            self.search_service.search(
                query,
                limit,
            )
        )

    async def get_cached(
        self,
        track: Track,
    ) -> Track | None:

        cached = await (
            self.cache_service.get(
                track
            )
        )
        if cached:
            logger.info(
                "Music cache hit: source=%s source_id=%s",
                track.source,
                track.source_id,
            )
        else:
            logger.info(
                "Music cache miss: source=%s source_id=%s",
                track.source,
                track.source_id,
            )

        return cached

    async def prepare(
        self,
        track: Track,
    ) -> Track:
        key = (
            track.source,
            track.source_id,
        )

        async with self._preparations_lock:
            task = self._preparations.get(key)

            if not task:
                task = asyncio.create_task(
                    self._prepare_track(track)
                )
                self._preparations[key] = task
                task.add_done_callback(
                    lambda finished, preparation_key=key:
                    self._discard_preparation(
                        preparation_key,
                        finished,
                    )
                )

        return await asyncio.shield(task)

    def _discard_preparation(
        self,
        key,
        task,
    ):
        if self._preparations.get(key) is task:
            self._preparations.pop(key, None)

    async def _prepare_track(
        self,
        track: Track,
    ) -> Track:
        cached = await self.get_cached(track)

        if cached:
            return cached

        await self.download(track)

        return track

    async def download(
        self,
        track: Track,
    ) -> str:

        logger.info(
            "Downloading music: source=%s source_id=%s",
            track.source,
            track.source_id,
        )

        path = await (
            self.download_service.download(
                track
            )
        )

        logger.info(
            "Music download complete: path=%s",
            path,
        )

        track.file_path = path

        await self.cache_service.save(
            track,
            path,
        )

        logger.info(
            "Music cache metadata saved: source=%s source_id=%s",
            track.source,
            track.source_id,
        )

        return path

    async def mark_used(
        self,
        track: Track,
    ):

        await self.cache_service.touch(
            track
        )
