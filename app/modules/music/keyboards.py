from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def search_results_keyboard(
    result_count: int,
) -> InlineKeyboardMarkup:

    buttons = []

    for index in range(result_count):
        buttons.append(
            InlineKeyboardButton(
                text=str(index + 1),
                callback_data=f"music:select:{index}",
            )
        )

    rows = []

    for i in range(0, len(buttons), 3):
        rows.append(buttons[i:i + 3])

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def playback_controls_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏸ Pause",
                    callback_data="music:control:pause",
                ),
                InlineKeyboardButton(
                    text="▶️ Resume",
                    callback_data="music:control:resume",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏭ Skip",
                    callback_data="music:control:skip",
                ),
                InlineKeyboardButton(
                    text="⏹ Stop",
                    callback_data="music:control:stop",
                ),
            ],
        ]
    )


def invite_voice_account_keyboard(username: str | None) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(
            text="➕ Invite LobMusic",
            callback_data="music:invite_voice",
        )
    ]]
    if username:
        rows[0].append(
            InlineKeyboardButton(
                text="👤 Open LobMusic",
                url=f"https://t.me/{username}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def promote_voice_account_keyboard(username: str | None) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(
            text="🛡 Prepare LobMusic",
            callback_data="music:promote_voice",
        )
    ]]
    if username:
        rows[0].append(
            InlineKeyboardButton(
                text="👤 Open LobMusic",
                url=f"https://t.me/{username}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
