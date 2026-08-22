import logging
from html import escape

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message

from app.core.cooldowns import CooldownActive
from app.modules.media.keyboards import details_keyboard, results_keyboard
from app.telegram.filters import CallbackModuleEnabled, ModuleEnabled
from app.telegram.helpers import smart_reply


logger = logging.getLogger(__name__)
router = Router()


class MediaMiddleware(BaseMiddleware):
    def __init__(self, factory): self.factory = factory
    async def __call__(self, handler, event, data):
        data["media_service"] = self.factory()
        return await handler(event, data)


def search_text(session, page):
    kind = session.kind.title()
    query = escape(str(session.metadata.get("query", "")))
    lines = [f'🔎 <b>{kind} results for “{query}”</b>', ""]
    start = page * session.page_size
    for index, item in enumerate(session.page(page), start=start + 1):
        year = f" ({escape(item.start_date[:4])})" if item.start_date else ""
        lines.append(f"<b>{index}.</b> {escape(item.title)}{year}")
    return "\n".join(lines)


def detail_text(item):
    icons = {"anime": "🍥", "manga": "📚", "manhwa": "📖", "movie": "🎬", "tv": "📺"}
    lines = [f"{icons[item.kind]} <b>{escape(item.title)}</b>"]
    if item.english_title and item.english_title != item.title: lines.append(f"English: {escape(item.english_title)}")
    if item.native_title and item.native_title != item.title: lines.append(f"Original: {escape(item.native_title)}")
    lines.append("")
    if item.score is not None: lines.append(f"⭐ {escape(item.rating_source or 'Score')}: {item.score:.1f}/10")
    if item.episodes is not None: lines.append(f"📺 Episodes: {item.episodes}")
    if item.chapters is not None: lines.append(f"📚 Chapters: {item.chapters}")
    if item.volumes is not None: lines.append(f"📕 Volumes: {item.volumes}")
    duration = item.duration_minutes or item.runtime_minutes
    if duration is not None: lines.append(f"⏱ Runtime: {duration // 60}h {duration % 60}m" if duration >= 60 else f"⏱ Duration: {duration} min")
    if item.start_date: lines.append(f"📅 Released: {escape(item.start_date)}")
    if item.end_date: lines.append(f"📅 Ended: {escape(item.end_date)}")
    if item.genres: lines.append(f"🎭 Genres: {escape(', '.join(item.genres))}")
    if item.studio: lines.append(f"🏢 Studio: {escape(item.studio)}")
    if item.director: lines.append(f"🎬 Director: {escape(item.director)}")
    if item.status: lines.append(f"📌 Status: {escape(item.status)}")
    if item.country: lines.append(f"🌍 Country: {escape(item.country)}")
    if item.content_rating: lines.append(f"🔞 Rating: {escape(item.content_rating)}")
    authors = item.metadata.get("authors", [])
    if authors: lines.extend(["", "<b>Authors</b>", *[f"• {escape(name)}" for name in authors]])
    if item.cast: lines.extend(["", "<b>Cast</b>", *[f"• {escape(name)}" for name in item.cast]])
    if item.description: lines.extend(["", "📝 <b>Synopsis</b>", "", escape(item.description[:1800])])
    return "\n".join(lines)[:4000]


async def run_search(message: Message, media_service, kind: str):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await smart_reply(message, f"Usage: /{kind} &lt;query&gt;", parse_mode="HTML"); return
    try:
        session = await media_service.search(kind, parts[1].strip(), message.chat.id, message.from_user.id)
    except CooldownActive as exc:
        await smart_reply(message, f"Please wait {exc.retry_after:.1f}s before searching again."); return
    except Exception:
        logger.exception("Media search failed: kind=%s chat=%s user=%s", kind, message.chat.id, message.from_user.id)
        await smart_reply(message, "I couldn't reach the media provider right now."); return
    if not session.items:
        await smart_reply(message, "No matching results were found."); return
    await smart_reply(message, search_text(session, 0), parse_mode="HTML", reply_markup=results_keyboard(session, 0))


for _kind in ("anime", "manga", "manhwa", "movie", "tv"):
    async def _handler(message: Message, media_service, kind=_kind):
        await run_search(message, media_service, kind)
    router.message.register(_handler, Command(_kind), ModuleEnabled("media"))


def owned_session(callback, media_service, session_id):
    session = media_service.pagination.get(session_id, chat_id=callback.message.chat.id)
    if not session:
        return None, "This search has expired. Please search again."
    if session.owner_id != callback.from_user.id:
        return None, "This search belongs to another user."
    return session, None


@router.callback_query(F.data.startswith("media:p:"), CallbackModuleEnabled("media"))
async def media_page(callback: CallbackQuery, media_service):
    _, _, session_id, page_text = callback.data.split(":")
    session, error = owned_session(callback, media_service, session_id)
    if error: await callback.answer(error, show_alert=True); return
    page = max(0, min(int(page_text), session.total_pages - 1))
    await callback.message.edit_text(search_text(session, page), parse_mode="HTML", reply_markup=results_keyboard(session, page), link_preview_options=LinkPreviewOptions(is_disabled=True))
    await callback.answer()


@router.callback_query(F.data.startswith("media:s:"), CallbackModuleEnabled("media"))
async def media_select(callback: CallbackQuery, media_service):
    _, _, session_id, index_text, page_text = callback.data.split(":")
    session, error = owned_session(callback, media_service, session_id)
    if error: await callback.answer(error, show_alert=True); return
    index = int(index_text)
    if index < 0 or index >= len(session.items): await callback.answer("Invalid result.", show_alert=True); return
    try:
        item = await media_service.details(session, index)
    except Exception:
        logger.exception("Media details failed: kind=%s id=%s", session.kind, session.items[index].id)
        await callback.answer("I couldn't load those details.", show_alert=True); return
    await callback.message.edit_text(
        detail_text(item), parse_mode="HTML", reply_markup=details_keyboard(session.id, int(page_text), item),
        link_preview_options=LinkPreviewOptions(url=item.poster_url, prefer_large_media=True, show_above_text=True) if item.poster_url else LinkPreviewOptions(is_disabled=True),
    )
    await media_service.selected(item, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "media:noop")
async def media_noop(callback: CallbackQuery): await callback.answer()
