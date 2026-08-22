from types import SimpleNamespace

from app.core.cooldowns import CooldownManager
from app.modules.base import BaseModule
from app.modules.reactions.handlers import ReactionMiddleware, router
from app.modules.reactions.provider import NekosBestReactionProvider
from app.telegram.membership import TelegramMembershipProvider


class ReactionService:
    def __init__(self, provider, membership, events, bot):
        self.provider, self.membership, self.events, self.bot = provider, membership, events, bot; self.cooldowns = CooldownManager()
    async def resolve_target(self, message):
        reply_user = getattr(getattr(message, "reply_to_message", None), "from_user", None)
        if reply_user: return reply_user
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().startswith("@"): return None
        user_id = await self.membership.resolve_user_id(parts[1].strip().split()[0])
        if not user_id: return None
        member = await self.bot.get_chat_member(message.chat.id, user_id)
        return member.user
    async def send(self, reaction, chat_id, sender_id, target_id):
        self.cooldowns.check((chat_id, sender_id, reaction), 2)
        media = await self.provider.random(reaction)
        await self.events.emit("reaction.sent", {"chat_id": chat_id, "user_id": sender_id, "target_user_id": target_id, "reaction": reaction})
        return media


class ReactionsModule(BaseModule):
    name = "reactions"; version = "1.0.0"; description = "Extensible anime-style social reactions."; enabled_by_default = False; core = False
    def __init__(self): self.service = None
    async def setup(self, container, dispatcher): router.message.middleware(ReactionMiddleware(lambda: self.service)); dispatcher.include_router(router)
    async def startup(self, container):
        membership = TelegramMembershipProvider(container.bot, container.voice_lifecycle.client if container.voice_lifecycle else None)
        self.service = ReactionService(NekosBestReactionProvider(container.http_client), membership, container.event_bus, container.bot)
    async def shutdown(self, container):
        if self.service: self.service.cooldowns.clear()
        self.service = None
