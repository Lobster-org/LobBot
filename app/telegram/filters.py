import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.core.permissions import Permission
from app.core.container import container
from app.services.module_service import ModuleService


logger = logging.getLogger(__name__)


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

        database = container.database

        if database is None:
            logger.error(
                "Module filter used before application startup"
            )
            return False

        service = ModuleService(
            database
        )

        return await service.is_enabled(
            message.chat.id,
            self.module_name
        )

class PermissionRequired(BaseFilter):

    def __init__(
        self,
        permission: Permission,
    ):
        self.permission = Permission(permission)

    async def __call__(
        self,
        message: Message,
        permission_service,
    ) -> bool:

        if message.chat.type not in {
            "group",
            "supergroup",
        }:
            await self._deny(
                message,
                "This command can only be used in a group.",
            )
            return False

        if not message.from_user:
            return False

        try:
            allowed = await permission_service.has_permission(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                permission=self.permission,
            )
            if not allowed:
                await self._deny(
                    message,
                    "⛔ You don't have permission to use this command.",
                )
            return allowed
        except Exception:
            logger.exception(
                "Permission check failed: chat=%s user=%s permission=%s",
                message.chat.id,
                message.from_user.id,
                self.permission.value,
            )
            await self._deny(
                message,
                "I couldn't verify your permission for this command.",
            )
            return False

    async def _deny(self, message: Message, text: str):
        reply = getattr(message, "reply", None)
        if not callable(reply):
            return

        try:
            await reply(text)
        except Exception:
            logger.exception(
                "Failed to send permission denial: chat=%s permission=%s",
                getattr(message.chat, "id", None),
                self.permission.value,
            )


class GroupAdmin(PermissionRequired):

    """Backward-compatible alias for module administration."""

    def __init__(self):
        super().__init__(
            Permission.MANAGE_MODULES
        )
