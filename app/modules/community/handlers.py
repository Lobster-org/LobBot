import logging

from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from app.modules.community.router import router
from app.telegram.filters import CallbackModuleEnabled, ModuleEnabled


logger = logging.getLogger(__name__)


@router.message(F.new_chat_members, ModuleEnabled("community"))
async def member_joined(message: Message, community_service):
    for user in message.new_chat_members:
        if not user.is_bot:
            await community_service.handle_join(message, user)


@router.message(F.left_chat_member, ModuleEnabled("community"))
async def member_left(message: Message, community_service):
    await community_service.handle_left(message, message.left_chat_member)


@router.callback_query(F.data.startswith("community:verify:"), CallbackModuleEnabled("community"))
async def verify_member(callback: CallbackQuery, community_service):
    try:
        intended = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("That verification button is invalid.", show_alert=True)
        return
    if callback.from_user.id != intended:
        await callback.answer("This verification is not for you.", show_alert=True)
        return
    if not callback.message or not await community_service.verification.verify(callback.message.chat.id, intended):
        await callback.answer("This verification has expired or was already completed.", show_alert=True)
        return
    try:
        await callback.message.edit_text("✅ Verified! The raccoon investigation is officially closed.")
    except TelegramAPIError:
        logger.warning("Could not edit completed verification message")
    await callback.answer("Welcome aboard!")
