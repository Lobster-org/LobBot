import logging
import re
from html import escape
from time import perf_counter

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.filters import Command
from aiogram.types import Message

from app.core.permissions import Permission
from app.modules.moderation.config import (
    DEFAULT_REASON,
    MAX_MUTE_SECONDS,
    MAX_PURGE_MESSAGES,
)
from app.modules.moderation.filters import can_moderate_target
from app.modules.moderation.router import router
from app.telegram.filters import ModuleEnabled, PermissionRequired
from app.telegram.helpers import smart_reply


logger = logging.getLogger(__name__)

DURATION_PATTERN = re.compile(r"^(\d+)([smhd])$", re.IGNORECASE)
DURATION_MULTIPLIERS = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 24 * 60 * 60,
}


def parse_duration(value: str) -> int:
    match = DURATION_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError("Duration must use s, m, h, or d")

    duration = int(match.group(1)) * DURATION_MULTIPLIERS[
        match.group(2).lower()
    ]
    if duration <= 0 or duration > MAX_MUTE_SECONDS:
        raise ValueError("Duration is outside the supported range")
    return duration


async def resolve_target(
    message: Message,
    permission_service,
) -> tuple[int | None, list[str]]:
    parts = (message.text or "").split()
    reply = message.reply_to_message

    if reply and reply.from_user:
        return reply.from_user.id, parts[1:]

    if len(parts) < 2:
        return None, []

    user_id = await permission_service.resolve_user_id(parts[1])
    return user_id, parts[2:]


async def reject_self_action(
    message: Message,
    target_id: int,
) -> bool:
    if message.from_user and target_id == message.from_user.id:
        await smart_reply(message, "You cannot moderate yourself.")
        return True
    return False


async def reject_protected_target(
    message: Message,
    permission_service,
    target_id: int,
) -> bool:
    if await reject_self_action(message, target_id):
        return True

    allowed = await can_moderate_target(
        permission_service,
        message.chat.id,
        message.from_user.id,
        target_id,
    )
    if not allowed:
        await smart_reply(
            message,
            "You cannot moderate a member with an equal or higher role.",
        )
        return True
    return False


async def telegram_failure(message: Message, error: Exception):
    logger.warning(
        "Telegram rejected moderation action: chat=%s error=%s",
        message.chat.id,
        error,
    )
    await smart_reply(
        message,
        "Telegram rejected that action. Check LobBot's admin permissions "
        "and the target member's role.",
    )


@router.message(
    Command("mute"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.MUTE_USERS),
)
async def mute_command(
    message: Message,
    permission_service,
    moderation_service,
):
    target_id, tail = await resolve_target(message, permission_service)
    if not target_id or not tail:
        await smart_reply(
            message,
            "Usage: /mute @user <10s|5m|2h|7d> [reason]",
        )
        return
    if await reject_protected_target(
        message, permission_service, target_id
    ):
        return

    try:
        duration = parse_duration(tail[0])
    except ValueError:
        await smart_reply(
            message,
            "Invalid duration. Use values such as 10s, 5m, 2h, or 7d.",
        )
        return

    reason = " ".join(tail[1:]) or DEFAULT_REASON
    try:
        action = await moderation_service.mute(
            message.chat.id,
            target_id,
            message.from_user.id,
            duration,
            reason,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        await telegram_failure(message, error)
        return

    await smart_reply(
        message,
        f"🔇 Muted <code>{target_id}</code> until "
        f"<code>{action.expires_at.isoformat()}</code>.\n"
        f"Reason: {escape(action.reason)}",
        parse_mode="HTML",
    )


@router.message(
    Command("ban"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.BAN_USERS),
)
async def ban_command(
    message: Message,
    permission_service,
    moderation_service,
):
    target_id, tail = await resolve_target(message, permission_service)
    if not target_id:
        await smart_reply(message, "Usage: /ban @user [reason]")
        return
    if await reject_protected_target(
        message, permission_service, target_id
    ):
        return

    reason = " ".join(tail) or DEFAULT_REASON
    try:
        await moderation_service.ban(
            message.chat.id,
            target_id,
            message.from_user.id,
            reason,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        await telegram_failure(message, error)
        return

    await smart_reply(
        message,
        f"🔨 Banned <code>{target_id}</code>.\n"
        f"Reason: {escape(reason)}",
        parse_mode="HTML",
    )


@router.message(
    Command("unban"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.BAN_USERS),
)
async def unban_command(
    message: Message,
    permission_service,
    moderation_service,
):
    target_id, _ = await resolve_target(message, permission_service)
    if not target_id:
        await smart_reply(message, "Usage: /unban @user")
        return

    try:
        await moderation_service.unban(
            message.chat.id,
            target_id,
            message.from_user.id,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        await telegram_failure(message, error)
        return

    await smart_reply(message, f"✅ Unbanned <code>{target_id}</code>.", parse_mode="HTML")


@router.message(
    Command("purge"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.PURGE_MESSAGES),
)
async def purge_command(message: Message, moderation_service):
    reply = message.reply_to_message

    if reply:
        first_id = reply.message_id
        amount = message.message_id - first_id + 1
    else:
        parts = (message.text or "").split(maxsplit=1)
        try:
            amount = int(parts[1])
        except (IndexError, ValueError):
            await smart_reply(
                message,
                "Purge usage:\n"
                "• /purge <amount> — delete that many recent messages.\n"
                "• Reply to the first message with /purge — delete "
                "everything from that message through the command.\n"
                f"Maximum: {MAX_PURGE_MESSAGES} messages.",
            )
            return
        first_id = max(1, message.message_id - amount + 1)

    if amount < 1 or amount > MAX_PURGE_MESSAGES:
        await smart_reply(
            message,
            f"Amount must be between 1 and {MAX_PURGE_MESSAGES}.",
        )
        return

    message_ids = list(range(first_id, message.message_id + 1))
    started_at = perf_counter()

    try:
        result = await moderation_service.purge(
            message.chat.id,
            message.from_user.id,
            message_ids,
        )
    except TelegramAPIError as error:
        await telegram_failure(message, error)
        return

    elapsed = perf_counter() - started_at
    await message.answer(
        f"✅ Deleted <b>{result.deleted_count}</b> messages "
        f"in <b>{elapsed:.2f}s</b>.",
        parse_mode="HTML",
    )
