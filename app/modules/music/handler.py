import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message
)

from app.telegram.filters import CallbackModuleEnabled, ModuleEnabled

from app.modules.music.models.queue import QueueItem

from app.modules.music.state import (
    music_state,
)

from app.modules.music.keyboards import (
    invite_voice_account_keyboard,
    playback_controls_keyboard,
    promote_voice_account_keyboard,
    search_results_keyboard,
)


logger = logging.getLogger(__name__)

router = Router()


async def require_voice_account_ready(message: Message) -> bool:
    membership = music_state.voice_membership
    if not membership:
        await message.reply("❌ The LobMusic voice account is not ready.")
        return False

    readiness = await membership.get_readiness(message.chat.id)
    if not readiness.is_member:
        await message.reply(
            f"🎙 <b>{membership.display_name}</b> is not in this group.\n\n"
            "LobMusic is required to join the Telegram voice chat and stream audio. "
            "Add it before using <code>/play</code>.",
            parse_mode="HTML",
            reply_markup=invite_voice_account_keyboard(membership.username),
        )
        return False
    if not readiness.can_manage_voice_chats:
        await message.reply(
            f"🛡 <b>{membership.display_name}</b> is in this group, but cannot "
            "start or manage its voice chat.\n\n"
            "Promote LobMusic and grant <b>Manage Video Chats</b>, then try "
            "<code>/play</code> again.",
            parse_mode="HTML",
            reply_markup=promote_voice_account_keyboard(membership.username),
        )
        return False
    return True

@router.message(
    Command("play"),
    ModuleEnabled("music"),
)
async def play_command(
    message: Message,
):
    logger.debug(
        "Play command received: chat=%s",
        message.chat.id,
    )

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await message.reply(
            "🎵 Usage: /play <song name>"
        )

        return

    query = parts[1].strip()

    if not query:

        await message.reply(
            "🎵 Please provide a song name."
        )

        return

    if not message.from_user:

        await message.reply(
            "❌ I couldn't identify you."
        )

        return

    if message.chat.type not in {"group", "supergroup"}:
        await message.reply("🎵 Music playback is only available in groups.")
        return

    if not await require_voice_account_ready(message):
        return

    status_message = await message.reply(
        "🔎 Searching..."
    )
    service = music_state.music_service

    if not service:
        await status_message.edit_text(
            "❌ Music is not ready."
        )
        return

    try:

        tracks = await service.search(
            query,
            limit=5,
        )

    except Exception:
        logger.exception(
            "Music search failed: user=%s chat=%s query=%r",
            message.from_user.id,
            message.chat.id,
            query,
        )

        await status_message.edit_text(
            "❌ I couldn't search for that song."
        )

        return

    logger.info(
        "Music search: user=%s chat=%s query=%r results=%d",
        message.from_user.id,
        message.chat.id,
        query,
        len(tracks),
    )

    if not tracks:

        await status_message.edit_text(
            "❌ No results found."
        )

        return

    # IMPORTANT:
    # Store the search results BEFORE
    # displaying the keyboard.
    music_state.search_sessions.create(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        tracks=tracks,
    )

    logger.debug(
        "Music search session created: "
        "user=%s chat=%s",
        message.from_user.id,
        message.chat.id,
    )

    lines = [
        "🎵 <b>Search Results</b>",
        "",
    ]

    for index, track in enumerate(
        tracks,
        start=1,
    ):

        duration = ""

        if track.duration:

            minutes = track.duration // 60
            seconds = track.duration % 60

            duration = (
                f" [{minutes}:{seconds:02d}]"
            )

        lines.append(
            f"<b>{index}.</b> "
            f"{track.title}"
            f"{duration}"
        )

    keyboard = search_results_keyboard(
        len(tracks)
    )

    await status_message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(
    F.data == "music:invite_voice",
    CallbackModuleEnabled("music"),
)
async def invite_voice_account(callback: CallbackQuery):
    if not callback.message:
        await callback.answer(
            "This invitation is no longer available.",
            show_alert=True,
        )
        return
    membership = music_state.voice_membership
    if not membership:
        await callback.answer("LobMusic is not ready.", show_alert=True)
        return
    await callback.answer("Inviting LobMusic…")
    try:
        joined = await membership.join(callback.message.chat.id)
    except Exception:
        logger.exception(
            "Could not invite voice account: chat=%s user=%s",
            callback.message.chat.id,
            callback.from_user.id,
        )
        await callback.message.edit_text(
            f"❌ I couldn't add <b>{membership.display_name}</b>.\n\n"
            "Make sure LobBot is an administrator with permission to invite "
            "users, and make sure LobMusic is not banned from this group. "
            "You can also add the account manually from its Telegram profile.",
            parse_mode="HTML",
            reply_markup=invite_voice_account_keyboard(membership.username),
        )
        return
    try:
        promoted = await membership.promote(callback.message.chat.id)
    except Exception:
        logger.exception(
            "Voice account joined but could not be promoted: chat=%s user=%s",
            callback.message.chat.id,
            callback.from_user.id,
        )
        await callback.message.edit_text(
            f"✅ <b>{membership.display_name}</b> is in the group, but I couldn't "
            "grant its voice-chat permission.\n\n"
            "Please promote LobMusic manually and enable <b>Manage Video Chats</b>.",
            parse_mode="HTML",
            reply_markup=promote_voice_account_keyboard(membership.username),
        )
        return
    await callback.message.edit_text(
        f"✅ <b>{membership.display_name}</b> "
        f"{'joined the group' if joined else 'is already in the group'} and "
        f"{'was prepared' if promoted else 'is ready'} for voice chat.\n\n"
        "Music is ready—send <code>/play &lt;song name&gt;</code> again.",
        parse_mode="HTML",
    )


@router.callback_query(
    F.data == "music:promote_voice",
    CallbackModuleEnabled("music"),
)
async def promote_voice_account(callback: CallbackQuery):
    if not callback.message:
        await callback.answer("This setup request expired.", show_alert=True)
        return
    membership = music_state.voice_membership
    if not membership:
        await callback.answer("LobMusic is not ready.", show_alert=True)
        return
    await callback.answer("Preparing LobMusic…")
    try:
        changed = await membership.promote(callback.message.chat.id)
    except Exception:
        logger.exception(
            "Could not promote voice account: chat=%s user=%s",
            callback.message.chat.id,
            callback.from_user.id,
        )
        await callback.message.edit_text(
            f"❌ I couldn't prepare <b>{membership.display_name}</b>.\n\n"
            "Make sure LobBot can add administrators, or manually promote "
            "LobMusic with <b>Manage Video Chats</b>.",
            parse_mode="HTML",
            reply_markup=promote_voice_account_keyboard(membership.username),
        )
        return
    await callback.message.edit_text(
        f"✅ <b>{membership.display_name}</b> "
        f"{'now has' if changed else 'already has'} voice-chat permission.\n\n"
        "Music is ready—send <code>/play &lt;song name&gt;</code> again.",
        parse_mode="HTML",
    )


@router.callback_query(
    F.data.startswith("music:select:")
)
async def select_search_result(
    callback: CallbackQuery,
):
    if not callback.from_user:
        await callback.answer(
            "Unable to identify you.",
            show_alert=True,
        )
        return

    if not callback.message:
        await callback.answer(
            "This request is no longer available.",
            show_alert=True,
        )
        return

    data = callback.data

    if not data:
        return

    try:
        index = int(
            data.split(":")[-1]
        )

    except ValueError:
        await callback.answer(
            "Invalid selection.",
            show_alert=True,
        )
        return

    session = music_state.search_sessions.get(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
    )

    if not session:

        await callback.answer(
            "This search has expired. Please search again.",
            show_alert=True,
        )

        return

    if (
        index < 0
        or index >= len(session.tracks)
    ):

        await callback.answer(
            "Invalid selection.",
            show_alert=True,
        )

        return

    track = session.tracks[index]

    if not await require_voice_account_ready(callback.message):
        await callback.answer(
            "LobMusic must be prepared before this song can play.",
            show_alert=True,
        )
        return

    # Claim the selection before the first await so a
    # double-click cannot enqueue the same result twice.
    music_state.search_sessions.delete(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
    )

    await callback.answer(
        f"Selected: {track.title}"
    )

    status_message = await callback.message.reply(
        f"⏳ Preparing "
        f"<b>{track.title}</b>...",
        parse_mode="HTML",
    )

    service = music_state.music_service

    if not service:
        await status_message.edit_text(
            "❌ Music is not ready."
        )
        return

    try:

        await status_message.edit_text(
            f"⬇️ Preparing "
            f"<b>{track.title}</b>...",
            parse_mode="HTML",
        )

        track = await service.prepare(track)

        if not track.file_path:

            await status_message.edit_text(
                "❌ Audio file was not prepared."
            )

            return

        queue_item = QueueItem(
            track=track,
            requested_by=callback.from_user.id,
        )

        position = await (
            music_state.queues.add(
                chat_id=callback.message.chat.id,
                item=queue_item,
            )
        )

        await status_message.edit_text(
            f"✅ <b>{track.title}</b>\n\n"
            f"📋 Added to queue at position "
            f"<b>{position}</b>.",
            parse_mode="HTML",
            reply_markup=playback_controls_keyboard(),
        )

        player = music_state.player

        if not player:
            raise RuntimeError(
                "Music playback service is not initialized"
            )

        await player.ensure_playing(
            callback.message.chat.id
        )

    except Exception:
        logger.exception(
            "Failed to prepare music: user=%s chat=%s source_id=%s",
            callback.from_user.id,
            callback.message.chat.id,
            track.source_id,
        )

        await status_message.edit_text(
            "❌ Failed to prepare the song."
        )


@router.message(
    Command("queue"),
    ModuleEnabled("music"),
)
async def queue_command(
    message: Message,
):

    queue = music_state.queues.snapshot(
        message.chat.id
    )

    lines = [
        "📋 <b>Music Queue</b>",
        "",
    ]

    if queue.current:

        lines.extend(
            [
                "▶️ <b>Now Playing</b>",
                f"• {queue.current.track.title}",
                "",
            ]
        )

    if not queue.items:

        if not queue.current:

            lines.append(
                "The queue is empty."
            )

    else:

        lines.append(
            "<b>Up Next</b>"
        )

        for index, item in enumerate(
            queue.items,
            start=1,
        ):

            lines.append(
                f"{index}. "
                f"{item.track.title}"
            )

    await message.reply(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=playback_controls_keyboard(),
    )


@router.message(
    Command("remove"),
    ModuleEnabled("music"),
)
async def remove_queue_item(
    message: Message,
):

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await message.reply(
            "Usage: /remove <position>"
        )

        return

    try:

        position = int(
            parts[1]
        )

    except ValueError:

        await message.reply(
            "❌ Position must be a number."
        )

        return

    if position < 1:

        await message.reply(
            "❌ Position must be at least 1."
        )

        return

    removed = await (
        music_state.queues.remove(
            chat_id=message.chat.id,
            index=position - 1,
        )
    )

    if not removed:

        await message.reply(
            "❌ No song exists at that position."
        )

        return

    await message.reply(
        f"🗑️ Removed "
        f"<b>{removed.track.title}</b> "
        f"from the queue.",
        parse_mode="HTML",
    )


async def run_playback_control(
    chat_id: int,
    action: str,
) -> str:

    player = music_state.player

    if not player:
        return "❌ Music playback is not ready."

    try:
        if action == "pause":
            changed = await player.pause(chat_id)
            return (
                "⏸ Playback paused."
                if changed
                else "ℹ️ Nothing is currently playing."
            )

        if action == "resume":
            changed = await player.resume(chat_id)
            return (
                "▶️ Playback resumed."
                if changed
                else "ℹ️ Playback is not paused."
            )

        if action == "skip":
            skipped = await player.skip(chat_id)
            return (
                f"⏭ Skipped {skipped.track.title}."
                if skipped
                else "ℹ️ Nothing is currently playing."
            )

        if action == "stop":
            changed = await player.stop(chat_id)
            return (
                "⏹ Playback stopped and the queue was cleared."
                if changed
                else "ℹ️ Nothing is currently playing."
            )
    except Exception:
        logger.exception(
            "Playback control failed: chat=%s action=%s",
            chat_id,
            action,
        )
        return "❌ Playback control failed. Please try again."

    return "❌ Unknown playback control."


@router.callback_query(
    F.data.startswith("music:control:")
)
async def playback_control_callback(
    callback: CallbackQuery,
):

    if not callback.message or not callback.data:
        await callback.answer(
            "This control is no longer available.",
            show_alert=True,
        )
        return

    action = callback.data.rsplit(":", 1)[-1]
    result = await run_playback_control(
        callback.message.chat.id,
        action,
    )

    await callback.answer(result)


async def playback_control_command(
    message: Message,
    action: str,
):

    result = await run_playback_control(
        message.chat.id,
        action,
    )

    await message.reply(result)


@router.message(
    Command("pause"),
    ModuleEnabled("music"),
)
async def pause_command(message: Message):
    await playback_control_command(message, "pause")


@router.message(
    Command("resume"),
    ModuleEnabled("music"),
)
async def resume_command(message: Message):
    await playback_control_command(message, "resume")


@router.message(
    Command("skip"),
    ModuleEnabled("music"),
)
async def skip_command(message: Message):
    await playback_control_command(message, "skip")


@router.message(
    Command("stop"),
    ModuleEnabled("music"),
)
async def stop_command(message: Message):
    await playback_control_command(message, "stop")
