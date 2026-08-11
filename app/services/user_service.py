from app.database.repositories.user import (
    UserRepository,
)

from app.database.repositories.group import (
    GroupRepository,
)

from app.core.event_names import (
    GROUP_REGISTERED,
    USER_REGISTERED,
)
from app.core.events import event_bus


class UserService:

    def __init__(
        self,
        database=None,
        users=None,
        groups=None,
        events=event_bus,
    ):

        self.users = users or UserRepository(database)

        self.groups = groups or GroupRepository(database)
        self.events = events

    async def register_user(
        self,
        telegram_user,
    ):

        user, created = await self.users.register_user(
            telegram_id=telegram_user.id,

            username=telegram_user.username,

            first_name=telegram_user.first_name,

            last_name=telegram_user.last_name,
        )

        if created:
            await self.events.emit(
                USER_REGISTERED,
                {
                    "telegram_id": telegram_user.id,
                    "username": telegram_user.username,
                    "first_name": telegram_user.first_name,
                },
            )

        return user

    async def register_group(
        self,
        chat,
    ):

        group, created = await self.groups.register_group(
            telegram_id=chat.id,

            title=chat.title,

            group_type=chat.type,
        )

        if created:
            await self.events.emit(
                GROUP_REGISTERED,
                {
                    "telegram_id": chat.id,
                    "title": chat.title,
                    "type": chat.type,
                },
            )

        return group
