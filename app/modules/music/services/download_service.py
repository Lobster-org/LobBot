from pathlib import Path

from app.modules.music.models.track import Track
from app.modules.music.providers.base import MusicProvider


class DownloadService:

    def __init__(
        self,
        provider: MusicProvider,
        storage_path: str,
    ):

        self.provider = provider

        self.storage_path = Path(
            storage_path
        )

        self.storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    async def download(
        self,
        track: Track,
    ) -> str:

        if not track.source_id:

            raise ValueError(
                "Track has no source ID"
            )

        output_path = (
            self.storage_path
            / f"{track.source_id}.webm"
        )

        if output_path.is_file():

            track.file_path = str(
                output_path
            )

            return str(output_path)

        path = await self.provider.download(
            track,
            str(output_path),
        )

        final_path = Path(path)

        if not final_path.is_file():

            raise RuntimeError(
                "Download completed but "
                "audio file was not found"
            )

        track.file_path = str(
            final_path
        )

        return str(final_path)
