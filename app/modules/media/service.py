from app.core.cache import TTLCache
from app.core.cooldowns import CooldownManager


class MediaService:
    def __init__(self, anilist, tmdb, events, pagination):
        self.anilist, self.tmdb = anilist, tmdb
        self.events, self.pagination = events, pagination
        self.cache = TTLCache(max_size=256, ttl_seconds=600)
        self.cooldowns = CooldownManager()

    def provider(self, kind):
        return self.anilist if kind in {"anime", "manga", "manhwa"} else self.tmdb

    async def search(self, kind, query, chat_id, user_id):
        self.cooldowns.check((chat_id, user_id, kind), 3)
        key = (kind, query.casefold())
        items = self.cache.get(key)
        if items is None:
            items = await self.provider(kind).search(kind, query)
            self.cache.set(key, items)
        session = self.pagination.create(user_id, chat_id, kind, items, metadata={"query": query})
        await self.events.emit("media.searched", {"chat_id": chat_id, "user_id": user_id, "kind": kind, "result_count": len(items)})
        return session

    async def details(self, session, index):
        item = session.items[index]
        if item.kind in {"movie", "tv"}:
            key = (item.kind, item.id, "details")
            detail = self.cache.get(key)
            if detail is None:
                detail = await self.tmdb.details(item.kind, item.id)
                self.cache.set(key, detail)
            return detail
        return item

    async def selected(self, item, chat_id, user_id):
        await self.events.emit("media.selected", {"chat_id": chat_id, "user_id": user_id, "kind": item.kind, "source_id": item.id})

    def shutdown(self):
        self.cache.clear(); self.cooldowns.clear(); self.pagination.clear()
