from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def results_keyboard(session, page):
    start = page * session.page_size
    indexes = range(start, min(start + session.page_size, len(session.items)))
    rows = []
    buttons = [InlineKeyboardButton(text=str(index + 1), callback_data=f"media:s:{session.id}:{index}:{page}") for index in indexes]
    for offset in range(0, len(buttons), 5):
        rows.append(buttons[offset:offset + 5])
    rows.append([
        InlineKeyboardButton(text="◀️", callback_data=f"media:p:{session.id}:{max(0, page - 1)}"),
        InlineKeyboardButton(text=f"Page {page + 1}/{session.total_pages}", callback_data="media:noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"media:p:{session.id}:{min(session.total_pages - 1, page + 1)}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def details_keyboard(session_id, page, item):
    rows = [[InlineKeyboardButton(text="◀ Back to Results", callback_data=f"media:p:{session_id}:{page}")]]
    links = []
    if item.trailer_url:
        links.append(InlineKeyboardButton(text="▶ Trailer", url=item.trailer_url))
    if item.info_url:
        links.append(InlineKeyboardButton(text="🔗 More Info", url=item.info_url))
    if links:
        rows.append(links)
    return InlineKeyboardMarkup(inline_keyboard=rows)
