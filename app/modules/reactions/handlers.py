import logging
from html import escape

from aiogram import BaseMiddleware, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.cooldowns import CooldownActive
from app.telegram.filters import ModuleEnabled


logger = logging.getLogger(__name__); router = Router()


class ReactionMiddleware(BaseMiddleware):
    def __init__(self, factory): self.factory = factory
    async def __call__(self, handler, event, data): data["reaction_service"] = self.factory(); return await handler(event, data)


@router.message(Command("pat"), ModuleEnabled("reactions"))
async def pat_command(message: Message, reaction_service):
    try: target = await reaction_service.resolve_target(message)
    except Exception:
        logger.exception("Reaction target lookup failed: chat=%s user=%s", message.chat.id, message.from_user.id)
        await message.reply("I couldn't find that user in this group."); return
    if not target:
        await message.reply("Reply to someone with /pat or use /pat @username."); return
    if target.id == message.from_user.id:
        await message.reply("A self-pat? Honestly, emotional self-maintenance. 🫳"); return
    if target.is_bot:
        await message.reply("Bots are delicate machinery. Pat a human instead. 🤖"); return
    try: media = await reaction_service.send("pat", message.chat.id, message.from_user.id, target.id)
    except CooldownActive as exc: await message.reply(f"Easy there—wait {exc.retry_after:.1f}s before another pat."); return
    except Exception:
        logger.exception("Reaction provider failed: reaction=pat chat=%s", message.chat.id)
        await message.reply(f"{escape(message.from_user.full_name)} gently pats {escape(target.full_name)} 🫳\n(The GIF escaped into the wilderness.)", parse_mode="HTML"); return
    caption = f"{escape(message.from_user.full_name)} pats {escape(target.full_name)} 🫳"
    try: await message.answer_animation(media.url, caption=caption, parse_mode="HTML")
    except Exception:
        logger.exception("Telegram rejected reaction media URL")
        await message.reply(caption, parse_mode="HTML")
