from aiogram import BaseMiddleware

from app.core.permissions import Role


ROLE_RANK = {
    Role.MEMBER: 0,
    Role.MODERATOR: 1,
    Role.ADMIN: 2,
    Role.OWNER: 3,
}


async def can_moderate_target(
    permission_service,
    chat_id: int,
    moderator_id: int,
    target_id: int,
) -> bool:
    """Apply LobBot role hierarchy without direct Telegram checks."""
    moderator_role = await permission_service.get_role(
        chat_id,
        moderator_id,
    )
    target_role = await permission_service.get_role(
        chat_id,
        target_id,
    )
    return ROLE_RANK[moderator_role] > ROLE_RANK[target_role]


class ModerationServiceMiddleware(BaseMiddleware):
    def __init__(self, service_getter, automod_getter):
        self.service_getter = service_getter
        self.automod_getter = automod_getter

    async def __call__(self, handler, event, data):
        service = self.service_getter()
        if service is None:
            raise RuntimeError("Moderation service is not initialized")

        data["moderation_service"] = service
        data["automod_service"] = self.automod_getter()
        return await handler(event, data)
