import logging

from aiogram.enums import ChatMemberStatus


logger = logging.getLogger(__name__)


class TelegramMembershipProvider:

    def __init__(self, bot, user_client=None):
        self.bot = bot
        self.user_client = user_client

    async def get_status(
        self,
        chat_id: int,
        user_id: int,
    ) -> ChatMemberStatus | None:
        try:
            member = await self.bot.get_chat_member(
                chat_id=chat_id,
                user_id=user_id,
            )
        except Exception:
            logger.exception(
                "Telegram membership lookup failed: chat=%s user=%s",
                chat_id,
                user_id,
            )
            return None

        return member.status

    async def resolve_user_id(self, username: str) -> int | None:
        """Resolve a public username through the existing Telethon client."""
        if self.user_client is None:
            return None
        normalized = username.strip().lstrip("@")
        if not normalized:
            return None
        try:
            entity = await self.user_client.get_entity(normalized)
        except Exception:
            logger.info(
                "Telegram username could not be resolved: username=%s",
                normalized,
            )
            return None
        user_id = getattr(entity, "id", None)
        return int(user_id) if user_id else None
