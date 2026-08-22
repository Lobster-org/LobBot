from app.core.cache import TTLCache
from app.core.cooldowns import CooldownManager
from app.core.pagination import PaginationStore
from app.modules.base import BaseModule
from app.modules.dictionary.handlers import DictionaryMiddleware, router
from app.modules.dictionary.provider import UrbanDictionaryProvider


class DictionaryService:
    def __init__(self, provider, events):
        self.provider, self.events = provider, events; self.pagination = PaginationStore(); self.cache = TTLCache(ttl_seconds=300); self.cooldowns = CooldownManager()
    async def search(self, term, chat_id, user_id):
        self.cooldowns.check((chat_id, user_id), 2)
        key = term.casefold(); items = self.cache.get(key)
        if items is None: items = await self.provider.search(term); self.cache.set(key, items)
        session = self.pagination.create(user_id, chat_id, "dictionary", items, page_size=1, metadata={"term": term})
        await self.events.emit("dictionary.searched", {"chat_id": chat_id, "user_id": user_id, "definition_count": len(items)})
        return session
    def shutdown(self): self.pagination.clear(); self.cache.clear(); self.cooldowns.clear()


class DictionaryModule(BaseModule):
    name = "dictionary"; version = "1.0.0"; description = "Urban Dictionary lookups."; enabled_by_default = False; core = False
    def __init__(self): self.service = None
    async def setup(self, container, dispatcher):
        middleware = DictionaryMiddleware(lambda: self.service); router.message.middleware(middleware); router.callback_query.middleware(middleware); dispatcher.include_router(router)
    async def startup(self, container): self.service = DictionaryService(UrbanDictionaryProvider(container.http_client), container.event_bus)
    async def shutdown(self, container):
        if self.service: self.service.shutdown()
        self.service = None
