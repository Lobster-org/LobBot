import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from telethon.errors import InviteHashExpiredError, UserAlreadyParticipantError
from telethon.tl.functions.messages import ImportChatInviteRequest


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VoiceAccountReadiness:
    is_member: bool
    can_manage_voice_chats: bool

    @property
    def ready(self) -> bool:
        return self.is_member and self.can_manage_voice_chats


class VoiceAccountMembershipService:
    """Checks and joins the configured MTProto voice account."""

    def __init__(self, bot, user_client, identity):
        self.bot = bot
        self.user_client = user_client
        self.user_id = int(identity.id)
        self.username = identity.username
        self._join_locks: dict[int, asyncio.Lock] = {}

    @property
    def display_name(self) -> str:
        return f"@{self.username}" if self.username else "LobMusic"

    async def is_member(self, chat_id: int) -> bool:
        return (await self.get_readiness(chat_id)).is_member

    async def get_readiness(self, chat_id: int) -> VoiceAccountReadiness:
        try:
            member = await self.bot.get_chat_member(chat_id, self.user_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            return VoiceAccountReadiness(False, False)

        is_member = member.status not in {
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED,
        }
        can_manage_voice_chats = member.status == ChatMemberStatus.CREATOR or (
            member.status == ChatMemberStatus.ADMINISTRATOR
            and bool(getattr(member, "can_manage_video_chats", False))
        )
        return VoiceAccountReadiness(is_member, can_manage_voice_chats)

    async def promote(self, chat_id: int) -> bool:
        lock = self._join_locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            readiness = await self.get_readiness(chat_id)
            if not readiness.is_member:
                raise RuntimeError("LobMusic is not in the group")
            if readiness.ready:
                return False

            await self.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=self.user_id,
                can_manage_video_chats=True,
            )
            if not (await self.get_readiness(chat_id)).ready:
                raise RuntimeError("LobMusic was not granted voice-chat permission")
            logger.info(
                "Voice account promoted for voice chats: chat=%s voice_user=%s",
                chat_id,
                self.user_id,
            )
            return True

    async def join(self, chat_id: int) -> bool:
        lock = self._join_locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            return await self._join_locked(chat_id)

    async def _join_locked(self, chat_id: int) -> bool:
        if await self.is_member(chat_id):
            return False

        for attempt in range(2):
            try:
                await self._join_with_fresh_invite(chat_id)
                break
            except UserAlreadyParticipantError:
                break
            except InviteHashExpiredError:
                if attempt:
                    raise
                logger.warning(
                    "Telegram rejected a fresh LobMusic invite; retrying: chat=%s",
                    chat_id,
                )

        if not await self.is_member(chat_id):
            raise RuntimeError("LobMusic did not join the group")
        logger.info(
            "Voice account joined group: chat=%s voice_user=%s",
            chat_id,
            self.user_id,
        )
        return True

    async def _join_with_fresh_invite(self, chat_id: int) -> None:
        invite = await self.bot.create_chat_invite_link(
            chat_id=chat_id,
            name="LobMusic voice account",
            expire_date=datetime.now(timezone.utc) + timedelta(minutes=10),
            member_limit=1,
        )
        try:
            invite_hash = self._invite_hash(invite.invite_link)
            await self.user_client(ImportChatInviteRequest(invite_hash))
        finally:
            try:
                await self.bot.revoke_chat_invite_link(
                    chat_id=chat_id,
                    invite_link=invite.invite_link,
                )
            except Exception:
                logger.exception(
                    "Failed to revoke LobMusic one-use invite: chat=%s",
                    chat_id,
                )

    @staticmethod
    def _invite_hash(invite_link: str) -> str:
        marker = "+" if "+" in invite_link else "joinchat/"
        invite_hash = invite_link.rsplit(marker, 1)[-1].split("?", 1)[0]
        if not invite_hash:
            raise ValueError("Telegram returned an invalid invite link")
        return invite_hash
