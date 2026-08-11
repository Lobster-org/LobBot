from aiogram.enums import ChatMemberStatus

from app.core.permissions import Permission, ROLE_PERMISSIONS, Role
from app.database.repositories.group import GroupRepository
from app.database.repositories.user import UserRepository


class PermissionService:

    def __init__(
        self,
        database=None,
        membership_provider=None,
        group_repository=None,
        user_repository=None,
    ):
        if group_repository is None:
            if database is None:
                raise ValueError(
                    "A database or group repository is required"
                )
            group_repository = GroupRepository(database)

        if user_repository is None:
            if database is None:
                raise ValueError(
                    "A database or user repository is required"
                )
            user_repository = UserRepository(database)

        self.groups = group_repository
        self.users = user_repository
        self.membership_provider = membership_provider

    async def get_role(
        self,
        chat_id: int,
        user_id: int,
    ) -> Role:
        if chat_id >= 0:
            return Role.MEMBER

        status = None

        if self.membership_provider:
            status = await self.membership_provider.get_status(
                chat_id,
                user_id,
            )

        if status == ChatMemberStatus.CREATOR:
            return Role.OWNER

        if status == ChatMemberStatus.ADMINISTRATOR:
            return Role.ADMIN

        custom_role = await self.groups.get_custom_role(
            chat_id,
            user_id,
        )

        if custom_role:
            try:
                role = Role(custom_role)
            except ValueError:
                role = Role.MEMBER

            if role == Role.MODERATOR:
                return role

        return Role.MEMBER

    async def has_permission(
        self,
        chat_id: int,
        user_id: int,
        permission: Permission,
    ) -> bool:
        if chat_id >= 0:
            return False

        permission = Permission(permission)
        role = await self.get_role(chat_id, user_id)

        if role == Role.OWNER:
            return True

        allowed = permission in ROLE_PERMISSIONS[role]
        overrides = await self.groups.get_permission_overrides(
            chat_id,
            user_id,
        )

        if permission.value in overrides:
            return overrides[permission.value]

        return allowed

    async def set_custom_role(
        self,
        chat_id: int,
        user_id: int,
        role: Role,
    ):
        if chat_id >= 0:
            raise ValueError(
                "Custom group roles require a Telegram group"
            )

        role = Role(role)

        if role != Role.MODERATOR:
            raise ValueError(
                "Only the custom moderator role can be assigned"
            )

        await self.groups.set_custom_role(
            chat_id,
            user_id,
            role.value,
        )

    async def remove_custom_role(
        self,
        chat_id: int,
        user_id: int,
    ):
        if chat_id >= 0:
            raise ValueError(
                "Custom group roles require a Telegram group"
            )

        await self.groups.remove_custom_role(
            chat_id,
            user_id,
        )

    async def set_permission_override(
        self,
        chat_id: int,
        user_id: int,
        permission: Permission,
        allowed: bool,
    ):
        if chat_id >= 0:
            raise ValueError(
                "Permission overrides require a Telegram group"
            )

        permission = Permission(permission)

        await self.groups.set_permission_override(
            chat_id,
            user_id,
            permission.value,
            bool(allowed),
        )

    async def remove_permission_override(
        self,
        chat_id: int,
        user_id: int,
        permission: Permission,
    ):
        if chat_id >= 0:
            raise ValueError(
                "Permission overrides require a Telegram group"
            )

        permission = Permission(permission)

        await self.groups.remove_permission_override(
            chat_id,
            user_id,
            permission.value,
        )

    async def resolve_user_id(
        self,
        reference: str,
    ) -> int | None:
        normalized = reference.strip()

        if normalized.isdigit():
            user_id = int(normalized)
            return user_id if user_id > 0 else None

        if not normalized.startswith("@"):
            return None

        user = await self.users.get_user_by_username(
            normalized
        )

        if not user:
            return None

        return int(user["telegram_id"])
