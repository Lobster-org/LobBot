import asyncio
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram.types import ChatPermissions

from app.modules.community.config import (
    VERIFICATION_BATCH_SIZE,
    VERIFICATION_POLL_SECONDS,
)
from app.modules.community.events import (
    MEMBER_VERIFIED,
    VERIFICATION_EXPIRED,
    VERIFICATION_STARTED,
)
from app.modules.community.keyboards import verification_keyboard


logger = logging.getLogger(__name__)


class VerificationService:
    def __init__(
        self,
        repository,
        bot,
        events,
        poll_seconds=VERIFICATION_POLL_SECONDS,
        batch_size=VERIFICATION_BATCH_SIZE,
    ):
        self.repository = repository
        self.bot = bot
        self.events = events
        self.poll_seconds = poll_seconds
        self.batch_size = batch_size
        self._task = None
        self._stop_event = asyncio.Event()

    async def begin(self, chat_id: int, user, timeout_seconds: int) -> bool:
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=timeout_seconds
        )
        _, created = await self.repository.create_pending(
            chat_id,
            user.id,
            expires_at,
        )
        if not created:
            return False

        try:
            await self.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=expires_at,
            )
            mention = (
                f'<a href="tg://user?id={user.id}">'
                f"{escape(user.full_name)}</a>"
            )
            await self.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🕵️ {mention}, prove you're not three raccoons "
                    f"in a trench coat. You have {timeout_seconds} seconds."
                ),
                parse_mode="HTML",
                reply_markup=verification_keyboard(user.id),
            )
        except Exception:
            await self.repository.mark_removed(chat_id, user.id)
            try:
                await self._restore_permissions(chat_id, user.id)
            except Exception:
                logger.exception(
                    "Failed to restore verification permissions: "
                    "chat=%s user=%s",
                    chat_id,
                    user.id,
                )
            raise

        await self.events.emit(
            VERIFICATION_STARTED,
            {
                "chat_id": chat_id,
                "user_id": user.id,
                "expires_at": expires_at,
            },
        )
        return True

    async def verify(self, chat_id: int, user_id: int) -> bool:
        if not await self.repository.claim_verification(chat_id, user_id):
            return False
        try:
            await self._restore_permissions(chat_id, user_id)
        except Exception:
            await self.repository.release_verification(chat_id, user_id)
            raise
        changed = await self.repository.mark_verified(chat_id, user_id)
        if changed:
            await self.events.emit(
                MEMBER_VERIFIED,
                {"chat_id": chat_id, "user_id": user_id},
            )
        return changed

    async def member_left(self, chat_id: int, user_id: int):
        await self.repository.mark_removed(chat_id, user_id)

    async def process_expired(self) -> int:
        records = await self.repository.claim_expired(
            datetime.now(timezone.utc),
            self.batch_size,
        )
        completed = 0
        for record in records:
            try:
                await self.bot.ban_chat_member(
                    chat_id=record["chat_id"],
                    user_id=record["user_id"],
                    revoke_messages=False,
                )
                await self.bot.unban_chat_member(
                    chat_id=record["chat_id"],
                    user_id=record["user_id"],
                    only_if_banned=True,
                )
                await self.repository.mark_expired(record["_id"])
            except Exception as error:
                await self.repository.release_claim(
                    record["_id"],
                    repr(error),
                )
                logger.exception(
                    "Verification expiration failed: chat=%s user=%s",
                    record["chat_id"],
                    record["user_id"],
                )
                continue

            completed += 1
            await self.events.emit(
                VERIFICATION_EXPIRED,
                {
                    "chat_id": record["chat_id"],
                    "user_id": record["user_id"],
                },
            )
        return completed

    async def start(self):
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._expiration_loop(),
            name="community-verification-worker",
        )

    async def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _expiration_loop(self):
        while not self._stop_event.is_set():
            try:
                await self.process_expired()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Verification expiration pass failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_seconds,
                )
            except TimeoutError:
                pass

    async def _restore_permissions(self, chat_id: int, user_id: int):
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
