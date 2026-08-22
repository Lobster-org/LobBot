import asyncio

import yt_dlp

from app.modules.music.models.track import Track
from app.modules.music.providers.base import MusicProvider


class YouTubeProvider(MusicProvider):

    name = "youtube"

    @staticmethod
    def _youtube_dl_options() -> dict:
        """Options required by yt-dlp's current YouTube extractor.

        YouTube now serves JavaScript challenges before issuing usable media
        URLs.  Node is application/runtime infrastructure (also installed in
        the Docker image), while yt-dlp-ejs supplies the challenge scripts.
        """

        return {
            "js_runtimes": {"node": {}},
        }

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[Track]:

        return await asyncio.to_thread(
            self._search,
            query,
            limit,
        )

    def _search(
        self,
        query: str,
        limit: int,
    ) -> list[Track]:

        options = {
            **self._youtube_dl_options(),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }

        search_query = (
            f"ytsearch{limit}:{query}"
        )

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            result = ydl.extract_info(
                search_query,
                download=False,
            )

        tracks = []

        for entry in result.get(
            "entries",
            [],
        ):

            if not entry:
                continue

            tracks.append(
                Track(
                    title=entry.get(
                        "title",
                        "Unknown",
                    ),
                    duration=entry.get(
                        "duration"
                    ),
                    url=entry.get(
                        "url"
                    ),
                    thumbnail=entry.get(
                        "thumbnail"
                    ),
                    source="youtube",
                    source_id=entry.get(
                        "id"
                    ),
                )
            )

        return tracks

    async def download(
        self,
        track: Track,
        output_path: str,
    ) -> str:

        return await asyncio.to_thread(
            self._download,
            track,
            output_path,
        )

    def _download(
        self,
        track: Track,
        output_path: str,
    ) -> str:

        options = {
            **self._youtube_dl_options(),
            "format": "bestaudio/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
        }

        url = (
            f"https://www.youtube.com/watch?v="
            f"{track.source_id}"
        )

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            ydl.download([url])

        return output_path
