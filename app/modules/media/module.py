from app.core.pagination import PaginationStore
from app.modules.base import BaseModule
from app.modules.media.handlers import MediaMiddleware, router
from app.modules.media.providers import AniListProvider, TMDBProvider
from app.modules.media.service import MediaService


class MediaModule(BaseModule):
    name = "media"; version = "1.0.0"; description = "Anime, manga, movie, and TV discovery."
    enabled_by_default = False; core = False

    def __init__(self): self.service = None
    async def setup(self, container, dispatcher):
        middleware = MediaMiddleware(lambda: self.service)
        router.message.middleware(middleware); router.callback_query.middleware(middleware)
        dispatcher.include_router(router)
    async def startup(self, container):
        if not container.http_client: raise RuntimeError("Media requires the shared HTTP client")
        self.service = MediaService(
            AniListProvider(container.http_client), TMDBProvider(container.http_client, container.settings.TMDB_BEARER_TOKEN),
            container.event_bus, PaginationStore(ttl_seconds=600, max_sessions=1000),
        )
    async def shutdown(self, container):
        if self.service: self.service.shutdown()
        self.service = None
