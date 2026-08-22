import logging
from html import escape

from aiogram import BaseMiddleware, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.cooldowns import CooldownActive
from app.telegram.filters import ModuleEnabled
from app.telegram.helpers import smart_reply


logger = logging.getLogger(__name__); router = Router()


class TranslationMiddleware(BaseMiddleware):
    def __init__(self, factory): self.factory = factory
    async def __call__(self, handler, event, data): data["translation_service"] = self.factory(); return await handler(event, data)


@router.message(Command("tr"), ModuleEnabled("translation"))
async def translate_command(message: Message, translation_service):
    raw = (message.text or "").split(maxsplit=1)
    supplied = raw[1].strip() if len(raw) > 1 else ""
    replied = getattr(getattr(message, "reply_to_message", None), "text", None) or getattr(getattr(message, "reply_to_message", None), "caption", None)
    try:
        target, text = await translation_service.parse(supplied, replied)
        result = await translation_service.translate(text, target, message.chat.id, message.from_user.id)
    except ValueError as exc: await smart_reply(message, escape(str(exc)), parse_mode="HTML"); return
    except CooldownActive as exc: await smart_reply(message, f"Please wait {exc.retry_after:.1f}s before translating again."); return
    except Exception:
        logger.exception("Translation failed: chat=%s user=%s", message.chat.id, message.from_user.id)
        await smart_reply(message, "I couldn't translate that right now."); return
    heading = (
        "🌐 <b>Translation</b>\n\n"
        f"Detected: {escape(result.source_name)}\n"
        f"Translated to: {escape(result.target_name)}\n\n"
    )
    chunks = translation_service.chunks(result.translated_text, 3900 - len(heading))
    await smart_reply(message, heading + escape(chunks[0]), parse_mode="HTML")
    for chunk in chunks[1:]: await message.answer(escape(chunk), parse_mode="HTML")
