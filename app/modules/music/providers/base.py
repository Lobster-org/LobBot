from abc import ABC, abstractmethod

from app.modules.music.models.track import Track


class MusicProvider(ABC):

    name: str = "unknown"

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[Track]:

        raise NotImplementedError

    @abstractmethod
    async def download(
        self,
        track: Track,
        output_path: str,
    ) -> str:

        raise NotImplementedError