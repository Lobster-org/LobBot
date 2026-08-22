import logging
from html import escape

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.core.cooldowns import CooldownActive
from app.telegram.filters import CallbackModuleEnabled, ModuleEnabled
from app.telegram.helpers import smart_reply


logger = logging.getLogger(__name__); router = Router()


class DictionaryMiddleware(BaseMiddleware):
    def __init__(self, factory): self.factory = factory
    async def __call__(self, handler, event, data): data["dictionary_service"] = self.factory(); return await handler(event, data)


def definition_text(session, index):
    item = session.items[index]
    lines = [f"📖 <b>{escape(item.word)}</b>", "", "<b>Definition</b>", escape(item.definition[:2300])]
    if item.example: lines.extend(["", "<b>Example</b>", escape(item.example[:900])])
    if item.author: lines.extend(["", f"By {escape(item.author)}"])
    lines.extend(["", f"👍 {item.thumbs_up:,}    👎 {item.thumbs_down:,}", f"Definition {index + 1}/{len(session.items)}"])
    return "\n".join(lines)


def keyboard(session, index):
    previous = (index - 1) % len(session.items); following = (index + 1) % len(session.items)
    rows = [[
        InlineKeyboardButton(text="◀️", callback_data=f"dictionary:d:{session.id}:{previous}"),
        InlineKeyboardButton(text="▶️", callback_data=f"dictionary:d:{session.id}:{following}"),
    ]]
    if session.items[index].url: rows.append([InlineKeyboardButton(text="🔗 Urban Dictionary", url=session.items[index].url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("ud"), ModuleEnabled("dictionary"))
async def ud_command(message: Message, dictionary_service):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip(): await smart_reply(message, "Usage: /ud &lt;word or phrase&gt;", parse_mode="HTML"); return
    try: session = await dictionary_service.search(parts[1].strip(), message.chat.id, message.from_user.id)
    except CooldownActive as exc: await smart_reply(message, f"Please wait {exc.retry_after:.1f}s before another lookup."); return
    except Exception:
        logger.exception("Dictionary lookup failed: chat=%s user=%s", message.chat.id, message.from_user.id)
        await smart_reply(message, "I couldn't reach Urban Dictionary right now."); return
    if not session.items: await smart_reply(message, "No definitions were found."); return
    await smart_reply(message, definition_text(session, 0), parse_mode="HTML", reply_markup=keyboard(session, 0))


@router.callback_query(F.data.startswith("dictionary:d:"), CallbackModuleEnabled("dictionary"))
async def definition_page(callback: CallbackQuery, dictionary_service):
    _, _, session_id, index_text = callback.data.split(":")
    session = dictionary_service.pagination.get(session_id, chat_id=callback.message.chat.id)
    if not session: await callback.answer("This lookup expired.", show_alert=True); return
    if session.owner_id != callback.from_user.id: await callback.answer("This lookup belongs to another user.", show_alert=True); return
    index = int(index_text)
    await callback.message.edit_text(definition_text(session, index), parse_mode="HTML", reply_markup=keyboard(session, index))
    await callback.answer()
