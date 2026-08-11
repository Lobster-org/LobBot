from html import escape

from aiogram.filters import Command
from aiogram.types import Message

from app.core.permissions import Permission
from app.modules.community.router import router
from app.telegram.filters import ModuleEnabled, PermissionRequired
from app.telegram.helpers import smart_reply


def _argument(message):
    parts = (message.text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


async def _toggle(message, service, field, usage):
    value = _argument(message).lower()
    if value not in {"on", "off"}:
        await smart_reply(message, f"Usage: {usage} on|off")
        return
    await service.update(message.chat.id, **{field: value == "on"})
    await smart_reply(message, f"✅ {field.replace('_enabled', '').replace('_', ' ').title()} is now {value}.")


@router.message(Command("rules"), ModuleEnabled("community"))
async def rules(message: Message, community_service):
    value = (await community_service.settings(message.chat.id)).rules
    await smart_reply(message, value or "No rules have been configured for this group.")


@router.message(Command("welcome"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def welcome(message: Message, community_service):
    await _toggle(message, community_service, "welcome_enabled", "/welcome")


@router.message(Command("goodbye"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def goodbye(message: Message, community_service):
    await _toggle(message, community_service, "goodbye_enabled", "/goodbye")


@router.message(Command("verification"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def verification(message: Message, community_service):
    await _toggle(message, community_service, "verification_enabled", "/verification")


@router.message(Command("servicecleanup"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def cleanup(message: Message, community_service):
    await _toggle(message, community_service, "delete_service_messages", "/servicecleanup")


async def _set_template(message, service, kind):
    text = _argument(message)
    if not text:
        await smart_reply(message, f"Usage: /set{kind} <message>")
        return
    try:
        await service.set_template(message.chat.id, kind, text)
    except ValueError:
        await smart_reply(message, "Invalid template. Supported variables: {name}, {first_name}, {username}, {mention}, {group}, {member_count}.")
        return
    await smart_reply(message, f"✅ Custom {kind} message saved.")


@router.message(Command("setwelcome"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def setwelcome(message: Message, community_service):
    await _set_template(message, community_service, "welcome")


@router.message(Command("setgoodbye"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def setgoodbye(message: Message, community_service):
    await _set_template(message, community_service, "goodbye")


@router.message(Command("setrules"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def setrules(message: Message, community_service):
    text = _argument(message)
    if not text:
        await smart_reply(message, "Usage: /setrules <text>")
        return
    await community_service.update(message.chat.id, rules=text)
    await smart_reply(message, "✅ Group rules saved.")


@router.message(Command("clearrules"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def clearrules(message: Message, community_service):
    await community_service.update(message.chat.id, rules=None)
    await smart_reply(message, "✅ Group rules cleared.")


@router.message(Command("community"), ModuleEnabled("community"), PermissionRequired(Permission.MANAGE_COMMUNITY))
async def status(message: Message, community_service):
    settings = await community_service.settings(message.chat.id)
    flag = lambda value: "enabled" if value else "disabled"
    await smart_reply(message, "<b>Community Settings</b>\n\n" +
        f"Welcome: {flag(settings.welcome_enabled)}\nGoodbye: {flag(settings.goodbye_enabled)}\n"
        f"Verification: {flag(settings.verification_enabled)}\nRules: {'configured' if settings.rules else 'not configured'}\n"
        f"Service cleanup: {flag(settings.delete_service_messages)}", parse_mode="HTML")
