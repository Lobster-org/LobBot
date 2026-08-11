import logging
import re
from html import escape
from time import perf_counter

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram import F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.core.permissions import Permission
from app.modules.moderation.config import (
    DEFAULT_REASON,
    MAX_MUTE_SECONDS,
    MAX_PURGE_MESSAGES,
)
from app.modules.moderation.filters import can_moderate_target
from app.modules.moderation.keyboards import banned_users_keyboard
from app.modules.moderation.router import router
from app.modules.moderation.services.punishment_service import (
    KickCleanupError,
)
from app.telegram.filters import (
    CallbackModuleEnabled,
    CallbackPermissionRequired,
    ModuleEnabled,
    PermissionRequired,
)
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

    # Telegram text mentions can carry the user object even when the member
    # has no public username or has never been registered by LobBot.
    for entity in message.entities or []:
        mentioned_user = getattr(entity, "user", None)
        if mentioned_user and mentioned_user.id:
            return mentioned_user.id, []

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
            "Sorry, I can't remove, ban, or restrict this user. "
            "They have an equal or higher administrative role.",
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
        "Sorry, I can't remove, ban, or restrict this user. "
        "They may be an administrator, the group owner, or above "
        "LobBot in the Telegram admin hierarchy.",
    )


@router.message(
    Command("warn"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.WARN_USERS),
)
async def warn_command(
    message: Message,
    permission_service,
    moderation_service,
):
    target_id, tail = await resolve_target(message, permission_service)
    if not target_id or not tail:
        await smart_reply(message, "Usage: /warn @user <reason>")
        return
    if await reject_protected_target(
        message, permission_service, target_id
    ):
        return

    action = await moderation_service.warn(
        message.chat.id,
        target_id,
        message.from_user.id,
        " ".join(tail),
    )
    await smart_reply(
        message,
        f"⚠️ Warned <code>{target_id}</code>.\n"
        f"Reason: {escape(action.reason)}\n"
        f"Warning ID: <code>{action.id}</code>",
        parse_mode="HTML",
    )


@router.message(
    Command("warnings"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.VIEW_MOD_LOGS),
)
async def warnings_command(
    message: Message,
    permission_service,
    moderation_service,
):
    target_id, _ = await resolve_target(message, permission_service)
    if not target_id:
        await smart_reply(message, "Usage: /warnings @user")
        return

    warnings = await moderation_service.warnings(
        message.chat.id,
        target_id,
    )
    lines = [
        f"<b>User:</b> <code>{target_id}</code>",
        f"<b>Warnings:</b> {len(warnings)}",
        "",
    ]
    lines.extend(
        (
            f"{index}. {escape(item.reason)} (<code>{item.id}</code>)"
            for index, item in enumerate(warnings, start=1)
        )
        if warnings
        else ["No active warnings."]
    )
    await smart_reply(message, "\n".join(lines), parse_mode="HTML")


@router.message(
    Command("warnremove"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.WARN_USERS),
)
async def warnremove_command(message: Message, moderation_service):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await smart_reply(message, "Usage: /warnremove <id>")
        return
    removed = await moderation_service.remove_warning(
        message.chat.id,
        parts[1].strip(),
        message.from_user.id,
    )
    await smart_reply(
        message,
        "✅ Warning removed."
        if removed
        else "No active warning with that ID was found.",
    )


def automod_status_text(config) -> str:
    rules = "\n".join(
        f"• {name}: {'on' if enabled else 'off'}"
        for name, enabled in config.rules.items()
    )
    return (
        f"<b>Automod:</b> {'enabled' if config.enabled else 'disabled'}\n\n"
        f"<b>Rules</b>\n{rules}\n\n"
        f"Blocked words: {len(config.blocked_words)}\n"
        f"Escalation: mute after {config.warning_threshold} warnings"
    )


@router.message(
    Command("automod"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.MANAGE_MODERATION),
)
async def automod_command(message: Message, automod_service):
    parts = (message.text or "").split()
    chat_id = message.chat.id

    if len(parts) == 1 or parts[1].lower() == "status":
        config = await automod_service.get_config(chat_id, refresh=True)
        await smart_reply(
            message,
            automod_status_text(config),
            parse_mode="HTML",
        )
        return

    operation = parts[1].lower()
    if operation in {"on", "off"} and len(parts) == 2:
        config = await automod_service.set_enabled(
            chat_id,
            operation == "on",
        )
        await smart_reply(message, automod_status_text(config), parse_mode="HTML")
        return

    if operation == "rule" and len(parts) == 4:
        state = parts[3].lower()
        if state not in {"on", "off"}:
            await smart_reply(message, "Rule state must be on or off.")
            return
        try:
            config = await automod_service.set_rule(
                chat_id,
                parts[2].lower(),
                state == "on",
            )
        except ValueError:
            await smart_reply(
                message,
                "Rules: flood, repeat, links, caps, words.",
            )
            return
        await smart_reply(message, automod_status_text(config), parse_mode="HTML")
        return

    if operation == "word" and len(parts) >= 3:
        action = parts[2].lower()
        if action == "list" and len(parts) == 3:
            config = await automod_service.get_config(chat_id, refresh=True)
            words = ", ".join(config.blocked_words) or "None"
            await smart_reply(message, f"Blocked words: {words}")
            return

        word = " ".join(parts[3:])
        if action in {"add", "remove"} and word:
            try:
                changed = (
                    await automod_service.add_word(chat_id, word)
                    if action == "add"
                    else await automod_service.remove_word(chat_id, word)
                )
            except ValueError as error:
                await smart_reply(message, str(error))
                return
            await smart_reply(
                message,
                "✅ Blocked-word list updated."
                if changed
                else "No change was needed.",
            )
            return

    await smart_reply(
        message,
        "Automod usage:\n"
        "• /automod [status|on|off]\n"
        "• /automod rule <flood|repeat|links|caps|words> <on|off>\n"
        "• /automod word <add|remove|list> [word]",
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
    Command("unmute"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.MUTE_USERS),
)
async def unmute_command(
    message: Message,
    permission_service,
    moderation_service,
):
    target_id, _ = await resolve_target(message, permission_service)
    if not target_id:
        await smart_reply(message, "Usage: /unmute @user")
        return
    if await reject_protected_target(
        message, permission_service, target_id
    ):
        return

    try:
        await moderation_service.unmute(
            message.chat.id,
            target_id,
            message.from_user.id,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        await telegram_failure(message, error)
        return

    await smart_reply(
        message,
        f"🔊 Unmuted <code>{target_id}</code>.",
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
    Command("kick"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.KICK_USERS),
)
async def kick_command(
    message: Message,
    permission_service,
    moderation_service,
):
    target_id, tail = await resolve_target(message, permission_service)
    if not target_id:
        await smart_reply(
            message,
            "Usage: /kick @user\nYou can also reply to a member with /kick.",
        )
        return
    if await reject_protected_target(
        message, permission_service, target_id
    ):
        return

    reason = " ".join(tail) or DEFAULT_REASON
    try:
        await moderation_service.kick(
            message.chat.id,
            target_id,
            message.from_user.id,
            reason,
        )
    except KickCleanupError:
        logger.exception(
            "Kick cleanup left an active ban: chat=%s user=%s",
            message.chat.id,
            target_id,
        )
        await smart_reply(
            message,
            "The user was removed, but Telegram did not clear the "
            "temporary ban. It has been added to /banned so you can "
            "unban them safely.",
        )
        return
    except TelegramAPIError as error:
        await telegram_failure(message, error)
        return

    text = f"👢 Kicked <code>{target_id}</code>."
    if tail:
        text += f"\nReason: {escape(reason)}"
    await smart_reply(message, text, parse_mode="HTML")


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


async def banned_view(moderation_service, chat_id: int, page: int):
    actions, page_count = await moderation_service.banned_users(
        chat_id,
        page,
    )
    normalized_page = page % page_count if page_count else 0
    lines = ["<b>Active bans</b>", ""]

    if not actions:
        lines.append("No active LobBot ban records.")
    else:
        for index, action in enumerate(
            actions,
            start=normalized_page * 10 + 1,
        ):
            lines.append(
                f"{index}. <code>{action.user_id}</code> — "
                f"{escape(action.reason)}"
            )

    return (
        "\n".join(lines),
        banned_users_keyboard(actions, normalized_page, page_count),
    )


@router.message(
    Command("banned"),
    ModuleEnabled("moderation"),
    PermissionRequired(Permission.BAN_USERS),
)
async def banned_command(message: Message, moderation_service):
    text, keyboard = await banned_view(
        moderation_service,
        message.chat.id,
        0,
    )
    await smart_reply(
        message,
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(
    F.data.startswith("moderation:bans:"),
    CallbackModuleEnabled("moderation"),
    CallbackPermissionRequired(Permission.BAN_USERS),
)
async def show_banned_page(
    callback: CallbackQuery,
    moderation_service,
):
    try:
        page = int(callback.data.rsplit(":", 1)[-1])
    except (AttributeError, ValueError):
        await callback.answer("Invalid page.", show_alert=True)
        return

    text, keyboard = await banned_view(
        moderation_service,
        callback.message.chat.id,
        page,
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("moderation:unban:"),
    CallbackModuleEnabled("moderation"),
    CallbackPermissionRequired(Permission.BAN_USERS),
)
async def unban_from_list(
    callback: CallbackQuery,
    moderation_service,
):
    parts = (callback.data or "").split(":")
    try:
        user_id = int(parts[2])
        page = int(parts[3])
    except (IndexError, ValueError):
        await callback.answer("Invalid unban action.", show_alert=True)
        return

    try:
        await moderation_service.unban(
            callback.message.chat.id,
            user_id,
            callback.from_user.id,
        )
    except TelegramAPIError:
        logger.exception(
            "Inline unban failed: chat=%s user=%s",
            callback.message.chat.id,
            user_id,
        )
        await callback.answer(
            "I couldn't unban this user.",
            show_alert=True,
        )
        return

    text, keyboard = await banned_view(
        moderation_service,
        callback.message.chat.id,
        page,
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer(f"Unbanned {user_id}.")


@router.callback_query(F.data == "moderation:noop")
async def moderation_noop(callback: CallbackQuery):
    await callback.answer()


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


@router.message(ModuleEnabled("moderation"))
async def inspect_for_automod(
    message: Message,
    permission_service,
    automod_service,
):
    if automod_service:
        await automod_service.inspect_message(
            message,
            permission_service,
        )
