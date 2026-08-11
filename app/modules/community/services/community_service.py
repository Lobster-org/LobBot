import logging
from datetime import datetime, timezone
from html import escape

from app.modules.community.events import MEMBER_JOINED, MEMBER_LEFT
from app.modules.community.templates import TemplateRenderer


logger = logging.getLogger(__name__)


class CommunityService:
    def __init__(self, repository, verification, bot, events):
        self.repository = repository
        self.verification = verification
        self.bot = bot
        self.events = events
        self.renderer = TemplateRenderer()

    async def settings(self, chat_id):
        return await self.repository.get_settings(chat_id)

    async def update(self, chat_id, **changes):
        settings = await self.settings(chat_id)
        for key, value in changes.items():
            setattr(settings, key, value)
        return await self.repository.save_settings(settings)

    async def set_template(self, chat_id, kind, text):
        self.renderer.validate(text)
        return await self.update(chat_id, **{f"{kind}_message": text})

    async def handle_join(self, message, user):
        settings = await self.settings(message.chat.id)
        if settings.verification_enabled:
            try:
                await self.verification.begin(
                    message.chat.id, user,
                    settings.verification_timeout_seconds,
                )
            except Exception:
                logger.exception("Could not start verification: chat=%s user=%s", message.chat.id, user.id)
        if settings.welcome_enabled:
            values = await self._values(message.chat, user)
            await message.answer(
                self.renderer.welcome(settings.welcome_message, values),
                parse_mode="HTML",
            )
        await self.events.emit(MEMBER_JOINED, self._event_payload(message.chat.id, user))
        await self._cleanup(message, settings)

    async def handle_left(self, message, user):
        await self.verification.member_left(message.chat.id, user.id)
        settings = await self.settings(message.chat.id)
        me = await self.bot.get_me()
        if settings.goodbye_enabled and user.id != me.id:
            values = await self._values(message.chat, user)
            await message.answer(
                self.renderer.goodbye(settings.goodbye_message, values),
                parse_mode="HTML",
            )
        await self.events.emit(MEMBER_LEFT, self._event_payload(message.chat.id, user))
        await self._cleanup(message, settings)

    async def _values(self, chat, user):
        try:
            count = await self.bot.get_chat_member_count(chat.id)
        except Exception:
            logger.warning("Could not retrieve member count: chat=%s", chat.id)
            count = "?"
        name = escape(user.full_name or user.first_name or "New member")
        return {
            "name": name,
            "first_name": escape(user.first_name or name),
            "username": escape(f"@{user.username}" if user.username else "no username"),
            "mention": f'<a href="tg://user?id={user.id}">{name}</a>',
            "group": escape(chat.title or "this group"),
            "member_count": str(count),
        }

    async def _cleanup(self, message, settings):
        if not settings.delete_service_messages:
            return
        try:
            await message.delete()
        except Exception:
            logger.warning("Could not delete community service message: chat=%s", message.chat.id)

    @staticmethod
    def _event_payload(chat_id, user):
        return {"chat_id": chat_id, "user_id": user.id, "username": user.username,
                "timestamp": datetime.now(timezone.utc)}
