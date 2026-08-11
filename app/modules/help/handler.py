from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.modules.help.help import (
    COMMANDS_BY_NAME,
    command_text,
    help_text,
)
from app.modules.help.keyboards import (
    command_keyboard,
    help_keyboard,
    help_page_count,
)
from app.modules.start.handler import (
    private_start_text,
    start_keyboard,
)


router = Router()


@router.message(Command("help", ignore_case=True))
async def help_command(message: Message):
    await message.answer(
        help_text(0, help_page_count()),
        parse_mode="HTML",
        reply_markup=help_keyboard(0),
    )


@router.callback_query(F.data.startswith("help:page:"))
async def show_help_page(callback: CallbackQuery):
    if not callback.message or not callback.data:
        await callback.answer()
        return

    try:
        page = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("Invalid help page.")
        return

    page_count = help_page_count()
    page %= page_count

    await callback.message.edit_text(
        help_text(page, page_count),
        parse_mode="HTML",
        reply_markup=help_keyboard(page),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("help:command:"))
async def show_command_help(callback: CallbackQuery):
    if not callback.message or not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":")

    if len(parts) != 4:
        await callback.answer("Invalid command.")
        return

    command = COMMANDS_BY_NAME.get(parts[2])

    try:
        page = int(parts[3])
    except ValueError:
        page = 0

    if not command:
        await callback.answer("Unknown command.")
        return

    await callback.message.edit_text(
        command_text(command),
        parse_mode="HTML",
        reply_markup=command_keyboard(page),
    )
    await callback.answer()


@router.callback_query(F.data == "help:start")
async def back_to_start(callback: CallbackQuery):
    if not callback.message:
        await callback.answer()
        return

    await callback.message.edit_text(
        private_start_text(callback.from_user.first_name),
        parse_mode="HTML",
        reply_markup=start_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "help:noop")
async def ignore_empty_help_button(callback: CallbackQuery):
    await callback.answer()
