import logging

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

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

        enabled = await service.is_enabled(
            message.chat.id,
            self.module_name
        )

        if not enabled and self._is_command(message):
            await self._notify_disabled(message)

        return enabled

    @staticmethod
    def _is_command(message: Message) -> bool:
        text = getattr(message, "text", None)
        return bool(text and text.lstrip().startswith("/"))

    async def _notify_disabled(self, message: Message):
        reply = getattr(message, "reply", None)
        if not callable(reply):
            return
        try:
            await reply(
                f"This command isn't available because the "
                f"{self.module_name} module is not enabled.\n"
                f"An administrator can enable it with "
                f"/enable {self.module_name}."
            )
        except Exception:
            logger.exception(
                "Failed to send module-disabled notice: chat=%s module=%s",
                getattr(message.chat, "id", None),
                self.module_name,
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


class CallbackPermissionRequired(BaseFilter):
    def __init__(self, permission: Permission):
        self.permission = Permission(permission)

    async def __call__(
        self,
        callback: CallbackQuery,
        permission_service,
    ) -> bool:
        message = callback.message
        if (
            not message
            or message.chat.type not in {"group", "supergroup"}
            or not callback.from_user
        ):
            await callback.answer(
                "This action is only available in groups.",
                show_alert=True,
            )
            return False

        allowed = await permission_service.has_permission(
            message.chat.id,
            callback.from_user.id,
            self.permission,
        )
        if not allowed:
            await callback.answer(
                "You don't have permission to use this action.",
                show_alert=True,
            )
        return allowed


class CallbackModuleEnabled(BaseFilter):
    def __init__(self, module_name: str):
        self.module_name = module_name

    async def __call__(self, callback: CallbackQuery) -> bool:
        if not callback.message:
            return False
        database = container.database
        if database is None:
            return False
        enabled = await ModuleService(database).is_enabled(
            callback.message.chat.id,
            self.module_name,
        )
        if not enabled:
            await callback.answer(
                f"The {self.module_name} module is not enabled. "
                f"An administrator can enable it with "
                f"/enable {self.module_name}.",
                show_alert=True,
            )
        return enabled
