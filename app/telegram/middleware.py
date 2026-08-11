from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware

from app.core.container import container
from app.services.user_service import UserService
from app.services.permission_service import PermissionService
from app.telegram.membership import TelegramMembershipProvider


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

        database = container.database

        if database is None:
            raise RuntimeError(
                "Database middleware used before application startup"
            )

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


class PermissionMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[
            [Any, dict[str, Any]],
            Awaitable[Any],
        ],
        event: Any,
        data: dict[str, Any],
    ):
        database = container.database

        if database is None:
            raise RuntimeError(
                "Permission middleware used before application startup"
            )
        bot = data.get("bot")

        data["permission_service"] = PermissionService(
            database=database,
            membership_provider=(
                TelegramMembershipProvider(
                    bot,
                    user_client=(
                        container.voice_lifecycle.client
                        if container.voice_lifecycle
                        else None
                    ),
                )
                if bot
                else None
            ),
        )

        return await handler(event, data)
