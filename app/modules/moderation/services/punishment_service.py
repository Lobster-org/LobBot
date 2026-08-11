import asyncio
import logging

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import ChatPermissions

from app.modules.moderation.config import (
    PURGE_BATCH_SIZE,
    PURGE_CONCURRENCY,
    PURGE_MAX_RETRIES,
)


logger = logging.getLogger(__name__)


class PunishmentService:
    """Isolates Telegram punishment API operations."""

    def __init__(self, bot):
        self.bot = bot

    async def mute(self, chat_id: int, user_id: int, expires_at):
        await self.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=expires_at,
        )

    async def unmute(self, chat_id: int, user_id: int):
        chat = await self.bot.get_chat(chat_id)
        permissions = chat.permissions or ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_invite_users=True,
        )
        await self.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions,
        )

    async def ban(self, chat_id: int, user_id: int):
        await self.bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            revoke_messages=True,
        )

    async def unban(self, chat_id: int, user_id: int):
        await self.bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            only_if_banned=True,
        )

    async def purge(self, chat_id: int, message_ids: list[int]) -> int:
        if not message_ids:
            return 0

        batches = [
            message_ids[index:index + PURGE_BATCH_SIZE]
            for index in range(0, len(message_ids), PURGE_BATCH_SIZE)
        ]
        semaphore = asyncio.Semaphore(PURGE_CONCURRENCY)

        async def delete_batch(batch: list[int]):
            async with semaphore:
                return await self._delete_batch(chat_id, batch)

        results = await asyncio.gather(
            *(delete_batch(batch) for batch in batches),
            return_exceptions=True,
        )
        deleted = sum(
            result
            for result in results
            if isinstance(result, int)
        )
        failures = [
            result
            for result in results
            if isinstance(result, Exception)
        ]

        if failures and not deleted:
            raise failures[0]

        if failures:
            logger.warning(
                "Purge partially completed: chat=%s deleted=%s "
                "requested=%s failed_batches=%s",
                chat_id,
                deleted,
                len(message_ids),
                len(failures),
            )

        return deleted

    async def _delete_batch(
        self,
        chat_id: int,
        message_ids: list[int],
    ) -> int:
        for attempt in range(PURGE_MAX_RETRIES + 1):
            try:
                deleted = await self.bot.delete_messages(
                    chat_id=chat_id,
                    message_ids=message_ids,
                )
                return len(message_ids) if deleted is not False else 0
            except TelegramRetryAfter as error:
                if attempt >= PURGE_MAX_RETRIES:
                    raise

                logger.warning(
                    "Purge rate limited: chat=%s retry_after=%s "
                    "attempt=%s",
                    chat_id,
                    error.retry_after,
                    attempt + 1,
                )
                await asyncio.sleep(error.retry_after)

        return 0
