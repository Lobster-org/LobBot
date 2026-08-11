import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.moderation.config import (
    EXPIRATION_BATCH_SIZE,
    EXPIRATION_POLL_SECONDS,
)
from app.modules.moderation.events import (
    ACTION_CREATED,
    ACTION_REMOVED,
    MESSAGE_PURGED,
    USER_BANNED,
    USER_MUTED,
    USER_UNMUTED,
)
from app.modules.moderation.models.punishment import (
    Punishment,
    PunishmentType,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PurgeResult:
    action: Punishment
    deleted_count: int
    requested_count: int


class ModerationService:
    def __init__(
        self,
        repository,
        punishments,
        events,
        poll_seconds: float = EXPIRATION_POLL_SECONDS,
        batch_size: int = EXPIRATION_BATCH_SIZE,
    ):
        self.repository = repository
        self.punishments = punishments
        self.events = events
        self.poll_seconds = poll_seconds
        self.batch_size = batch_size
        self._expiration_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def mute(
        self,
        chat_id: int,
        user_id: int,
        moderator_id: int,
        duration_seconds: int,
        reason: str,
    ) -> Punishment:
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=duration_seconds
        )
        await self.punishments.mute(chat_id, user_id, expires_at)
        try:
            return await self._create(
                Punishment(
                    chat_id=chat_id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    action=PunishmentType.MUTE,
                    reason=reason,
                    expires_at=expires_at,
                    created_at=datetime.now(timezone.utc),
                ),
                USER_MUTED,
            )
        except Exception:
            logger.exception(
                "Mute persistence failed; reverting restriction: "
                "chat=%s user=%s",
                chat_id,
                user_id,
            )
            try:
                await self.punishments.unmute(chat_id, user_id)
            except Exception:
                logger.exception(
                    "Failed to revert unpersisted mute: chat=%s user=%s",
                    chat_id,
                    user_id,
                )
            raise

    async def ban(
        self,
        chat_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
    ) -> Punishment:
        await self.punishments.ban(chat_id, user_id)
        try:
            return await self._create(
                Punishment(
                    chat_id=chat_id,
                    user_id=user_id,
                    moderator_id=moderator_id,
                    action=PunishmentType.BAN,
                    reason=reason,
                    created_at=datetime.now(timezone.utc),
                ),
                USER_BANNED,
            )
        except Exception:
            logger.exception(
                "Ban persistence failed; reverting ban: chat=%s user=%s",
                chat_id,
                user_id,
            )
            try:
                await self.punishments.unban(chat_id, user_id)
            except Exception:
                logger.exception(
                    "Failed to revert unpersisted ban: chat=%s user=%s",
                    chat_id,
                    user_id,
                )
            raise

    async def unban(
        self,
        chat_id: int,
        user_id: int,
        moderator_id: int,
    ) -> Punishment | None:
        await self.punishments.unban(chat_id, user_id)
        action = await self.repository.remove_active_action(
            chat_id,
            user_id,
            PunishmentType.BAN,
            moderator_id,
        )
        if action:
            await self._emit(ACTION_REMOVED, action)
        return action

    async def purge(
        self,
        chat_id: int,
        moderator_id: int,
        message_ids: list[int],
    ) -> PurgeResult:
        deleted_count = await self.punishments.purge(
            chat_id,
            message_ids,
        )
        action = await self._create(
            Punishment(
                chat_id=chat_id,
                moderator_id=moderator_id,
                action=PunishmentType.PURGE,
                reason=f"Deleted {deleted_count} messages",
                created_at=datetime.now(timezone.utc),
            ),
            MESSAGE_PURGED,
            extra={
                "message_count": deleted_count,
                "requested_count": len(message_ids),
            },
        )
        return PurgeResult(
            action=action,
            deleted_count=deleted_count,
            requested_count=len(message_ids),
        )

    async def process_expired_mutes(self) -> int:
        actions = await self.repository.claim_expired_mutes(
            datetime.now(timezone.utc),
            self.batch_size,
        )
        completed = 0

        for action in actions:
            try:
                await self.punishments.unmute(
                    action.chat_id,
                    action.user_id,
                )
                await self.repository.complete_expiration(action.id)
            except Exception as error:
                await self.repository.release_expiration(
                    action.id,
                    repr(error),
                )
                logger.exception(
                    "Automatic unmute failed: chat=%s user=%s action=%s",
                    action.chat_id,
                    action.user_id,
                    action.id,
                )
                continue

            completed += 1
            await self._emit(USER_UNMUTED, action)
            await self._emit(ACTION_REMOVED, action)

        return completed

    async def start(self):
        if self._expiration_task and not self._expiration_task.done():
            return

        self._stop_event.clear()
        self._expiration_task = asyncio.create_task(
            self._expiration_loop(),
            name="moderation-expiration-worker",
        )
        logger.info("Moderation expiration worker started")

    async def stop(self):
        self._stop_event.set()
        task = self._expiration_task

        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        self._expiration_task = None
        logger.info("Moderation expiration worker stopped")

    async def _expiration_loop(self):
        while not self._stop_event.is_set():
            try:
                await self.process_expired_mutes()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Mute expiration pass failed")

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_seconds,
                )
            except TimeoutError:
                pass

    async def _create(
        self,
        action: Punishment,
        specific_event: str,
        extra: dict | None = None,
    ) -> Punishment:
        action = await self.repository.create(action)
        await self._emit(ACTION_CREATED, action, extra)
        await self._emit(specific_event, action, extra)
        return action

    async def _emit(
        self,
        event_name: str,
        action: Punishment,
        extra: dict | None = None,
    ):
        payload = {
            "action_id": str(action.id),
            "chat_id": action.chat_id,
            "user_id": action.user_id,
            "moderator_id": action.moderator_id,
            "action": action.action.value,
            "reason": action.reason,
            "expires_at": action.expires_at,
        }
        if extra:
            payload.update(extra)
        await self.events.emit(event_name, payload)
