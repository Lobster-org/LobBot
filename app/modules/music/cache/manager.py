from pathlib import Path

from app.modules.music.models.track import Track


class MusicCache:

    def __init__(
        self,
        storage_path: str,
    ):

        self.storage_path = Path(
            storage_path
        )

    def get_path(
        self,
        track: Track,
    ) -> Path:

        return (
            self.storage_path
            / f"{track.source_id}.webm"
        )

    def exists(
        self,
        track: Track,
    ) -> bool:

        return self.get_path(
            track
        ).exists()