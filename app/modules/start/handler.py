from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)


router = Router()


def private_start_text(
    first_name: str | None,
) -> str:
    safe_name = escape(first_name or "there")

    return (
        f"Hello, <b>{safe_name}</b>! 👋\n\n"
        "LobBot is a modular Telegram community bot for music, "
        "group management, permissions, moderation, games, and "
        "other community tools.\n\n"
        "Use <b>Help</b> to explore the available commands."
    )


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Help",
                    callback_data="help:page:0",
                )
            ]
        ]
    )


@router.message(
    Command("start", ignore_case=True)
)
async def start_command(
    message: Message,
    user_context,
):
    user = user_context["user"]
    group = user_context["group"]
    first_name = (
        user.get("first_name")
        if user
        else None
    )

    if group:
        await message.reply(
            "LobBot is active in this group. 👋\n"
            "Use /help to browse available commands."
        )
        return

    await message.answer(
        private_start_text(first_name),
        parse_mode="HTML",
        reply_markup=start_keyboard(),
    )
