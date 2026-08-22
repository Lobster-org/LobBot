from html import escape

from aiogram import BaseMiddleware, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message

from app.telegram.filters import ModuleEnabled
from app.telegram.helpers import smart_reply


router = Router()


class AFKMiddleware(BaseMiddleware):
    def __init__(self, factory): self.factory = factory
    async def __call__(self, handler, event, data): data["afk_service"] = self.factory(); return await handler(event, data)


async def set_away(message, afk_service, status):
    reason = (message.text or "").split(maxsplit=1); reason = reason[1].strip()[:500] if len(reason) > 1 else None
    await afk_service.start(message.chat.id, message.from_user, status, reason)
    text = f"💤 {escape(message.from_user.full_name)} is now {status.upper()}."
    if reason: text += f"\nReason: {escape(reason)}"
    await smart_reply(message, text, parse_mode="HTML")


@router.message(Command("afk"), ModuleEnabled("afk"))
async def afk_command(message: Message, afk_service): await set_away(message, afk_service, "afk")


@router.message(Command("brb"), ModuleEnabled("afk"))
async def brb_command(message: Message, afk_service): await set_away(message, afk_service, "brb")


@router.message(Command("mentions"), ModuleEnabled("afk"))
async def mentions_command(message: Message, afk_service):
    record = await afk_service.repository.get(message.chat.id, message.from_user.id)
    mentions = (record or {}).get("mentions", [])
    if not mentions: await smart_reply(message, "No missed mentions are recorded for your current AFK session."); return
    lines = ["💬 <b>While you were away</b>", ""]
    for index, mention in enumerate(mentions[-10:], 1):
        lines.append(f"{index}. {escape(mention.get('from_name') or 'Someone')}: {escape(mention.get('snippet') or '')}")
    await smart_reply(message, "\n".join(lines), parse_mode="HTML")


@router.message(ModuleEnabled("afk"))
async def observe_afk(message: Message, afk_service):
    if not message.from_user or message.from_user.is_bot or not (message.text or message.caption): raise SkipHandler
    is_command = bool((message.text or "").lstrip().startswith("/"))
    if not is_command:
        old = await afk_service.end(message.chat.id, message.from_user.id)
        if old:
            count = len(old.get("mentions", [])); duration = afk_service.duration(afk_service.elapsed_seconds(old))
            await message.reply(f"👋 Welcome back, {escape(message.from_user.full_name)}!\nYou were away for {duration}.\nYou received {count} mention{'s' if count != 1 else ''}.", parse_mode="HTML")
    for record in await afk_service.targets(message):
        if record["user_id"] == message.from_user.id: continue
        if not await afk_service.mention(message, record): continue
        reason = f"\nReason: {escape(record['reason'])}" if record.get("reason") else ""
        await message.reply(f"💤 {escape(record.get('display_name') or 'That user')} is {record.get('status', 'afk').upper()}.{reason}\nAway for: {afk_service.duration(afk_service.elapsed_seconds(record))}.", parse_mode="HTML")
    raise SkipHandler
