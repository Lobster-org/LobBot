from app.core.cooldowns import CooldownManager
from app.modules.base import BaseModule
from app.modules.translation.handlers import TranslationMiddleware, router
from app.modules.translation.provider import LibreTranslateProvider


class TranslationService:
    def __init__(self, provider, events, default_target="en"):
        self.provider, self.events, self.default_target = provider, events, default_target; self.cooldowns = CooldownManager()
    async def parse(self, supplied, replied):
        target = self.default_target; text = supplied
        if supplied:
            first, separator, rest = supplied.partition(" ")
            resolved = await self.provider.resolve_language(first)
            if resolved and separator: target, text = resolved, rest.strip()
        if not text: text = replied or ""
        if not text: raise ValueError("Usage: /tr [target language] <text>, or reply to a message with /tr.")
        if text.lstrip().startswith("/"): raise ValueError("I won't translate a command. Reply to ordinary text instead.")
        return target, text
    async def translate(self, text, target, chat_id, user_id):
        self.cooldowns.check((chat_id, user_id), 2)
        result = await self.provider.translate(text, target)
        await self.events.emit("translation.completed", {"chat_id": chat_id, "user_id": user_id, "source_language": result.source_code, "target_language": target})
        return result
    @staticmethod
    def chunks(text, size): return [text[index:index + size] for index in range(0, len(text), size)] or [""]


class TranslationModule(BaseModule):
    name = "translation"; version = "1.0.0"; description = "Text translation with language detection."; enabled_by_default = False; core = False
    def __init__(self): self.service = None
    async def setup(self, container, dispatcher):
        router.message.middleware(TranslationMiddleware(lambda: self.service)); dispatcher.include_router(router)
    async def startup(self, container):
        provider = LibreTranslateProvider(container.http_client, container.settings.runtime_libretranslate_url, container.settings.LIBRETRANSLATE_API_KEY)
        self.service = TranslationService(provider, container.event_bus, container.settings.TRANSLATION_DEFAULT_LANGUAGE)
    async def shutdown(self, container):
        if self.service: self.service.cooldowns.clear()
        self.service = None
