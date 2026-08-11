from datetime import datetime, timezone

from app.database.collections import MUSIC_CACHE
from app.database.repositories.base import BaseRepository


class MusicRepository(BaseRepository):

    def __init__(self, database):

        super().__init__(
            database,
            MUSIC_CACHE,
        )

    async def get_by_source_id(
        self,
        source: str,
        source_id: str,
    ):

        return await self.find_one(
            {
                "source": source,
                "source_id": source_id,
            }
        )

    async def save_cache_entry(
        self,
        track,
        file_path: str,
    ):

        now = datetime.now(
            timezone.utc
        )

        return await self.update_one(
            {
                "source": track.source,
                "source_id": track.source_id,
            },
            {
                "$set": {
                    "title": track.title,
                    "artist": track.artist,
                    "duration": track.duration,
                    "thumbnail": track.thumbnail,
                    "file_path": file_path,
                    "last_used": now,
                },
                "$setOnInsert": {
                    "source": track.source,
                    "source_id": track.source_id,
                    "created_at": now,
                    "play_count": 0,
                },
            },
            upsert=True,
        )

    async def touch(
        self,
        source: str,
        source_id: str,
    ):

        await self.update_one(
            {
                "source": source,
                "source_id": source_id,
            },
            {
                "$set": {
                    "last_used": datetime.now(
                        timezone.utc
                    )
                },
                "$inc": {
                    "play_count": 1
                },
            },
        )
