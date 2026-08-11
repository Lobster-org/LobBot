from app.modules.music.models.track import Track
from app.modules.music.providers.base import MusicProvider


class SearchService:

    def __init__(
        self,
        provider: MusicProvider,
    ):

        self.provider = provider

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[Track]:

        return await self.provider.search(
            query,
            limit,
        )