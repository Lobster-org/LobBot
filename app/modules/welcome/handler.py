from aiogram import F
from aiogram.types import Message

from app.modules.welcome.router import router
from app.telegram.filters import ModuleEnabled


@router.message(
    F.new_chat_members,
    ModuleEnabled("welcome"),
)
async def welcome_new_members(
    message: Message,
    welcome_service,
):
    for user in message.new_chat_members:
        if user.is_bot:
            continue
        await welcome_service.welcome(message.chat.id, user)
