from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def banned_users_keyboard(
    actions,
    page: int,
    page_count: int,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"Unban {action.user_id}",
                callback_data=(
                    f"moderation:unban:{action.user_id}:{page}"
                ),
            )
        ]
        for action in actions
    ]

    if page_count > 1:
        rows.append(
            [
                InlineKeyboardButton(
                    text="◀️",
                    callback_data=(
                        f"moderation:bans:{(page - 1) % page_count}"
                    ),
                ),
                InlineKeyboardButton(
                    text=f"{page + 1}/{page_count}",
                    callback_data="moderation:noop",
                ),
                InlineKeyboardButton(
                    text="▶️",
                    callback_data=(
                        f"moderation:bans:{(page + 1) % page_count}"
                    ),
                ),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)
