from pathlib import Path

from app.database.repositories.music import (
    MusicRepository,
)

from app.modules.music.models.track import Track


class MusicCacheService:

    def __init__(
        self,
        database,
        storage_path: str,
    ):

        self.repository = MusicRepository(
            database
        )

        self.storage_path = Path(
            storage_path
        )

    async def get(
        self,
        track: Track,
    ) -> Track | None:

        if not track.source:
            return None

        if not track.source_id:
            return None

        cached = (
            await self.repository.get_by_source_id(
                track.source,
                track.source_id,
            )
        )

        if not cached:
            return None

        cached_path = cached.get("file_path")

        if not cached_path:
            return None

        file_path = Path(cached_path)

        # MongoDB says it exists, but the
        # actual file may have been deleted.
        if not file_path.exists():

            return None

        track.file_path = str(
            file_path
        )

        return track

    async def save(
        self,
        track: Track,
        file_path: str,
    ):

        if not track.source:
            raise ValueError(
                "Track source is missing"
            )

        if not track.source_id:
            raise ValueError(
                "Track source_id is missing"
            )

        existing = (
            await self.repository.get_by_source_id(
                track.source,
                track.source_id,
            )
        )

        if existing:

            existing_path = Path(
                existing["file_path"]
            )

            if existing_path.is_file():

                track.file_path = str(
                    existing_path
                )

                await self.repository.save_cache_entry(
                    track,
                    str(existing_path),
                )

                return track

        await self.repository.save_cache_entry(
            track,
            file_path,
        )

        track.file_path = file_path

        return track

    async def touch(
        self,
        track: Track,
    ):
        if not track.source:
            return

        if not track.source_id:
            return

        await self.repository.touch(
            track.source,
            track.source_id,
        )
