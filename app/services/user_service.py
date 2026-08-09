from app.database.repositories.user import (
    UserRepository,
)

from app.database.repositories.group import (
    GroupRepository,
)


class UserService:

    def __init__(self, database):

        self.users = UserRepository(
            database
        )

        self.groups = GroupRepository(
            database
        )

    async def register_user(
        self,
        telegram_user,
    ):

        return await self.users.get_or_create_user(
            telegram_id=telegram_user.id,

            username=telegram_user.username,

            first_name=telegram_user.first_name,

            last_name=telegram_user.last_name,
        )

    async def register_group(
        self,
        chat,
    ):

        return await self.groups.get_or_create_group(
            telegram_id=chat.id,

            title=chat.title,

            group_type=chat.type,
        )