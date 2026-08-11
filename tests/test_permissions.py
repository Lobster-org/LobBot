from types import SimpleNamespace

import pytest
from aiogram.enums import ChatMemberStatus

from app.core.permissions import Permission, Role
from app.services.permission_service import PermissionService
from app.telegram.filters import PermissionRequired


CHAT_ID = -100123456789


class FakeMembershipProvider:

    def __init__(self, statuses=None):
        self.statuses = statuses or {}

    async def get_status(self, chat_id, user_id):
        return self.statuses.get((chat_id, user_id))


class FakeGroupRepository:

    def __init__(self):
        self.roles = {}
        self.overrides = {}

    async def get_custom_role(self, chat_id, user_id):
        return self.roles.get((chat_id, user_id))

    async def set_custom_role(self, chat_id, user_id, role):
        self.roles[(chat_id, user_id)] = role

    async def remove_custom_role(self, chat_id, user_id):
        self.roles.pop((chat_id, user_id), None)

    async def get_permission_overrides(self, chat_id, user_id):
        return self.overrides.get((chat_id, user_id), {})

    async def set_permission_override(
        self,
        chat_id,
        user_id,
        permission,
        allowed,
    ):
        self.overrides.setdefault(
            (chat_id, user_id),
            {},
        )[permission] = allowed

    async def remove_permission_override(
        self,
        chat_id,
        user_id,
        permission,
    ):
        self.overrides.get(
            (chat_id, user_id),
            {},
        ).pop(permission, None)


class FakeUserRepository:

    def __init__(self, users=None):
        self.users = users or {}

    async def get_user_by_username(self, username):
        return self.users.get(username.lstrip("@").lower())


def permission_service(statuses=None):
    groups = FakeGroupRepository()
    service = PermissionService(
        membership_provider=FakeMembershipProvider(statuses),
        group_repository=groups,
        user_repository=FakeUserRepository(),
    )
    return service, groups


async def test_creator_has_full_permissions():
    service, _ = permission_service(
        {(CHAT_ID, 1): ChatMemberStatus.CREATOR}
    )

    assert await service.get_role(CHAT_ID, 1) == Role.OWNER
    assert await service.has_permission(
        CHAT_ID,
        1,
        Permission.MANAGE_MODULES,
    ) is True
    assert await service.has_permission(
        CHAT_ID,
        1,
        Permission.MANAGE_AI,
    ) is True


async def test_telegram_admin_has_administrative_permissions():
    service, _ = permission_service(
        {(CHAT_ID, 2): ChatMemberStatus.ADMINISTRATOR}
    )

    assert await service.get_role(CHAT_ID, 2) == Role.ADMIN
    assert await service.has_permission(
        CHAT_ID,
        2,
        Permission.MANAGE_MODULES,
    ) is True
    assert await service.has_permission(
        CHAT_ID,
        2,
        Permission.MANAGE_ROLES,
    ) is True


async def test_custom_moderator_has_moderation_not_module_permission():
    service, groups = permission_service(
        {(CHAT_ID, 3): ChatMemberStatus.MEMBER}
    )
    groups.roles[(CHAT_ID, 3)] = Role.MODERATOR.value

    assert await service.get_role(CHAT_ID, 3) == Role.MODERATOR
    assert await service.has_permission(
        CHAT_ID,
        3,
        Permission.BAN_USERS,
    ) is False
    assert await service.has_permission(
        CHAT_ID,
        3,
        Permission.MANAGE_MODULES,
    ) is False


async def test_normal_member_is_denied_admin_permissions():
    service, _ = permission_service(
        {(CHAT_ID, 4): ChatMemberStatus.MEMBER}
    )

    assert await service.get_role(CHAT_ID, 4) == Role.MEMBER
    assert await service.has_permission(
        CHAT_ID,
        4,
        Permission.DELETE_MESSAGES,
    ) is False


async def test_custom_role_assignment_and_removal():
    service, groups = permission_service()

    await service.set_custom_role(
        CHAT_ID,
        5,
        Role.MODERATOR,
    )
    assert groups.roles[(CHAT_ID, 5)] == "moderator"
    assert await service.get_role(CHAT_ID, 5) == Role.MODERATOR

    await service.remove_custom_role(CHAT_ID, 5)
    assert await service.get_role(CHAT_ID, 5) == Role.MEMBER

    with pytest.raises(ValueError):
        await service.set_custom_role(
            CHAT_ID,
            5,
            Role.ADMIN,
        )


async def test_group_permission_override_changes_role_default():
    service, groups = permission_service()
    groups.roles[(CHAT_ID, 6)] = Role.MODERATOR.value

    await service.set_permission_override(
        CHAT_ID,
        6,
        Permission.MANAGE_MUSIC,
        True,
    )
    await service.set_permission_override(
        CHAT_ID,
        6,
        Permission.BAN_USERS,
        False,
    )

    assert await service.has_permission(
        CHAT_ID,
        6,
        Permission.MANAGE_MUSIC,
    ) is True
    assert await service.has_permission(
        CHAT_ID,
        6,
        Permission.BAN_USERS,
    ) is False


class FilterPermissionService:

    def __init__(self, allowed):
        self.allowed = allowed
        self.calls = []

    async def has_permission(self, chat_id, user_id, permission):
        self.calls.append((chat_id, user_id, permission))
        return self.allowed


async def test_permission_filter_allows_and_denies():
    required = PermissionRequired(
        Permission.MANAGE_MODULES
    )
    replies = []

    async def reply(text):
        replies.append(text)

    message = SimpleNamespace(
        chat=SimpleNamespace(
            id=CHAT_ID,
            type="supergroup",
        ),
        from_user=SimpleNamespace(id=7),
        reply=reply,
    )

    allowed = FilterPermissionService(True)
    denied = FilterPermissionService(False)

    assert await required(message, allowed) is True
    assert await required(message, denied) is False
    assert allowed.calls == [
        (CHAT_ID, 7, Permission.MANAGE_MODULES)
    ]
    assert replies == [
        "⛔ You don't have permission to use this command."
    ]


async def test_permission_filter_rejects_private_chat_cleanly():
    required = PermissionRequired(
        Permission.MANAGE_MODULES
    )
    service = FilterPermissionService(True)
    replies = []

    async def reply(text):
        replies.append(text)

    message = SimpleNamespace(
        chat=SimpleNamespace(id=7, type="private"),
        from_user=SimpleNamespace(id=7),
        reply=reply,
    )

    assert await required(message, service) is False
    assert service.calls == []
    assert replies == ["This command can only be used in a group."]
