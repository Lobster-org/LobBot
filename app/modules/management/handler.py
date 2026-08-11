import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.container import container
from app.core.modules import module_loader
from app.services.module_service import ModuleService
from app.telegram.helpers import smart_reply
from app.core.permissions import Permission, Role
from app.telegram.filters import PermissionRequired


logger = logging.getLogger(__name__)

router = Router()

@router.message(
    Command("modules")
)
async def list_modules(
    message: Message,
):

    modules = module_loader.all()

    enabled_modules = set()

    # Group-specific module configuration
    if message.chat.type in {
        "group",
        "supergroup",
    }:

        database = container.database

        if database is None:
            raise RuntimeError("Database is not initialized")

        service = ModuleService(
            database
        )

        enabled_modules = set(
            await service.get_enabled_modules(
                message.chat.id
            )
        )

    lines = [
        "📦 <b>LobBot Modules</b>",
        "",
    ]

    for module in modules:

        # Core modules are always active
        if module.core:

            status = "🔒"

        # Group configuration takes priority
        elif message.chat.type in {
            "group",
            "supergroup",
        }:

            if module.name in enabled_modules:
                status = "✅"
            else:
                status = "❌"

        # Private chats use default state
        elif module.enabled_by_default:

            status = "✅"

        else:

            status = "❌"

        lines.append(
            f"{status} <b>{module.name}</b>"
        )

        lines.append(
            f"   {module.description}"
        )

    await smart_reply(
        message,
        "\n".join(lines),
        parse_mode="HTML",
    )

@router.message(
    Command("enable"),
    PermissionRequired(Permission.MANAGE_MODULES),
)
async def enable_module(
    message: Message,
):

    if message.chat.type not in {
        "group",
        "supergroup",
    }:

        await smart_reply(
            message,
            "This command can only be used in a group.",
        )

        return


    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await smart_reply(
            message,
            "Usage: /enable <module>",
        )

        return


    module_name = parts[1].strip().lower()


    module = module_loader.get(
        module_name
    )


    if module is None:

        await smart_reply(
            message,
            f"❌ Unknown module: "
            f"<code>{module_name}</code>",
            parse_mode="HTML",
        )

        return


    if module.core:

        await smart_reply(
            message,
            "🔒 This is a core module and "
            "cannot be disabled.",
        )

        return


    database = container.database

    if database is None:
        raise RuntimeError("Database is not initialized")

    service = ModuleService(
        database
    )


    await service.enable_module(
        message.chat.id,
        module_name,
        changed_by=(
            message.from_user.id
            if message.from_user
            else None
        ),
    )


    await smart_reply(
        message,
        f"✅ <b>{module_name}</b> "
        f"has been enabled.",
        parse_mode="HTML",
    )

@router.message(
    Command("disable"),
    PermissionRequired(Permission.MANAGE_MODULES),
)
async def disable_module(
    message: Message,
):

    if message.chat.type not in {
        "group",
        "supergroup",
    }:

        await smart_reply(
            message,
            "This command can only be used in a group.",
        )

        return


    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        await smart_reply(
            message,
            "Usage: /disable <module>",
        )

        return


    module_name = parts[1].strip().lower()


    module = module_loader.get(
        module_name
    )


    if module is None:

        await smart_reply(
            message,
            f"❌ Unknown module: "
            f"<code>{module_name}</code>",
            parse_mode="HTML",
        )

        return


    if module.core:

        await smart_reply(
            message,
            "🔒 This is a core module "
            "and cannot be disabled.",
        )

        return


    database = container.database

    if database is None:
        raise RuntimeError("Database is not initialized")

    service = ModuleService(
        database
    )


    await service.disable_module(
        message.chat.id,
        module_name,
        changed_by=(
            message.from_user.id
            if message.from_user
            else None
        ),
    )


    await smart_reply(
        message,
        f"✅ <b>{module_name}</b> "
        f"has been disabled.",
        parse_mode="HTML",
    )


async def resolve_role_target(
    message: Message,
    permission_service,
    reference: str | None,
) -> int | None:
    if (
        message.reply_to_message
        and message.reply_to_message.from_user
    ):
        return message.reply_to_message.from_user.id

    if not reference:
        return None

    return await permission_service.resolve_user_id(
        reference
    )


@router.message(
    Command("role"),
    PermissionRequired(Permission.MANAGE_ROLES),
)
async def set_role(
    message: Message,
    permission_service,
):
    parts = (message.text or "").split()
    replying = bool(
        message.reply_to_message
        and message.reply_to_message.from_user
    )

    if replying:
        reference = None
        role_name = parts[1] if len(parts) > 1 else None
    else:
        reference = parts[1] if len(parts) > 1 else None
        role_name = parts[2] if len(parts) > 2 else None

    if not role_name:
        await smart_reply(
            message,
            "Usage: /role @user moderator",
        )
        return

    user_id = await resolve_role_target(
        message,
        permission_service,
        reference,
    )

    if not user_id:
        await smart_reply(
            message,
            "❌ I could not resolve that user. "
            "Ask them to message LobBot first or reply to their message.",
        )
        return

    try:
        role = Role(role_name.lower())
        await permission_service.set_custom_role(
            message.chat.id,
            user_id,
            role,
        )
    except ValueError as error:
        await smart_reply(
            message,
            f"❌ {error}",
        )
        return

    logger.info(
        "Custom role assigned: chat=%s target=%s role=%s actor=%s",
        message.chat.id,
        user_id,
        role.value,
        message.from_user.id if message.from_user else None,
    )

    await smart_reply(
        message,
        f"✅ User <code>{user_id}</code> is now a "
        f"<b>{role.value}</b>.",
        parse_mode="HTML",
    )


@router.message(
    Command("unrole"),
    PermissionRequired(Permission.MANAGE_ROLES),
)
async def remove_role(
    message: Message,
    permission_service,
):
    parts = (message.text or "").split()
    reference = parts[1] if len(parts) > 1 else None
    user_id = await resolve_role_target(
        message,
        permission_service,
        reference,
    )

    if not user_id:
        await smart_reply(
            message,
            "Usage: /unrole @user, or reply with /unrole",
        )
        return

    await permission_service.remove_custom_role(
        message.chat.id,
        user_id,
    )

    logger.info(
        "Custom role removed: chat=%s target=%s actor=%s",
        message.chat.id,
        user_id,
        message.from_user.id if message.from_user else None,
    )

    await smart_reply(
        message,
        f"✅ Removed the custom role from "
        f"<code>{user_id}</code>.",
        parse_mode="HTML",
    )
