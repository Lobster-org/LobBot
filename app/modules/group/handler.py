from aiogram import Router
from aiogram.types import ChatMemberUpdated

from app.database.mongodb import mongodb
from app.services.user_service import UserService


router = Router()


@router.my_chat_member()
async def bot_membership_changed(
    event: ChatMemberUpdated,
):
    """
    Handles changes to the bot's membership
    in a group or supergroup.
    """

    chat = event.chat

    if chat.type not in {
        "group",
        "supergroup",
    }:
        return

    database = mongodb.get_database()

    service = UserService(
        database
    )

    new_status = event.new_chat_member.status

    if new_status in {
        "member",
        "administrator",
    }:

        await service.register_group(
            chat
        )

        group = await service.groups.get_group(
            chat.id
        )

        if group:

            await service.groups.update_bot_status(
                telegram_id=chat.id,
                status="active",
            )

    elif new_status in {
        "left",
        "kicked",
    }:

        await service.groups.update_bot_status(
            telegram_id=chat.id,
            status="removed",
        )