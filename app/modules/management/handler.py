from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.mongodb import mongodb
from app.core.modules import module_loader
from app.services.module_service import ModuleService
from app.telegram.helpers import smart_reply
from app.telegram.filters import GroupAdmin

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

        database = mongodb.get_database()

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
    GroupAdmin(),
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


    database = mongodb.get_database()

    service = ModuleService(
        database
    )


    await service.enable_module(
        message.chat.id,
        module_name,
    )


    await smart_reply(
        message,
        f"✅ <b>{module_name}</b> "
        f"has been enabled.",
        parse_mode="HTML",
    )
    
@router.message(
    Command("disable"),
    GroupAdmin(),
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


    database = mongodb.get_database()

    service = ModuleService(
        database
    )


    await service.disable_module(
        message.chat.id,
        module_name,
    )


    await smart_reply(
        message,
        f"✅ <b>{module_name}</b> "
        f"has been disabled.",
        parse_mode="HTML",
    )