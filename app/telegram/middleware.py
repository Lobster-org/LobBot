from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware

from app.database.mongodb import mongodb
from app.services.user_service import UserService


class DatabaseMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[
            [Any, dict[str, Any]],
            Awaitable[Any],
        ],
        event: Any,
        data: dict[str, Any],
    ):

        database = mongodb.get_database()

        service = UserService(
            database
        )

        user = None
        group = None

        # --------------------------------
        # USER REGISTRATION
        # --------------------------------

        if getattr(event, "from_user", None):

            user = await service.register_user(
                event.from_user
            )

        # --------------------------------
        # GROUP REGISTRATION
        # --------------------------------

        if getattr(event, "chat", None):

            if event.chat.type in {
                "group",
                "supergroup",
            }:

                group = await service.register_group(
                    event.chat
                )

        # --------------------------------
        # CONTEXT
        # --------------------------------

        data["user_context"] = {
            "user": user,
            "group": group,
        }

        return await handler(
            event,
            data,
        )