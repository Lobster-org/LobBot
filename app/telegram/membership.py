import logging

from aiogram.enums import ChatMemberStatus


logger = logging.getLogger(__name__)


class TelegramMembershipProvider:

    def __init__(self, bot):
        self.bot = bot

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
