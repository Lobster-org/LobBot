from aiogram.filters import BaseFilter
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus

from app.database.mongodb import mongodb
from app.services.module_service import ModuleService


class ModuleEnabled(BaseFilter):

    def __init__(
        self,
        module_name: str,
    ):
        self.module_name = module_name

    async def __call__(
        self,
        message: Message,
    ) -> bool:

        # Private chats don't require
        # group module configuration.
        if message.chat.type == "private":
            return True

        if message.chat.type not in {
            "group",
            "supergroup",
        }:
            return False

        database = mongodb.get_database()

        service = ModuleService(
            database
        )

        enabled_modules = (
            await service.get_enabled_modules(
                message.chat.id
            )
        )

        return await service.is_enabled(
            message.chat.id,
            self.module_name
        )

class GroupAdmin(BaseFilter):

    async def __call__(
        self,
        message: Message,
    ) -> bool:

        if message.chat.type not in {
            "group",
            "supergroup",
        }:
            return False

        if not message.from_user:
            return False

        member = await message.chat.get_member(
            message.from_user.id
        )

        return member.status in {
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        }