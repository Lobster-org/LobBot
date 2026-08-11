from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.modules.help.help import COMMANDS


COMMANDS_PER_PAGE = 12
COMMAND_COLUMNS = 3


def help_page_count() -> int:
    return max(
        1,
        ceil(len(COMMANDS) / COMMANDS_PER_PAGE),
    )


def help_keyboard(page: int) -> InlineKeyboardMarkup:
    page_count = help_page_count()
    page = page % page_count
    start = page * COMMANDS_PER_PAGE
    commands = list(
        COMMANDS[start:start + COMMANDS_PER_PAGE]
    )

    buttons = [
        InlineKeyboardButton(
            text=f"/{command.name}",
            callback_data=f"help:command:{command.name}:{page}",
        )
        for command in commands
    ]

    while len(buttons) < COMMANDS_PER_PAGE:
        buttons.append(
            InlineKeyboardButton(
                text=" ",
                callback_data="help:noop",
            )
        )

    rows = [
        buttons[index:index + COMMAND_COLUMNS]
        for index in range(
            0,
            COMMANDS_PER_PAGE,
            COMMAND_COLUMNS,
        )
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"help:page:{(page - 1) % page_count}",
            ),
            InlineKeyboardButton(
                text="Back",
                callback_data="help:start",
            ),
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"help:page:{(page + 1) % page_count}",
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def command_keyboard(page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Back to commands",
                    callback_data=f"help:page:{page}",
                )
            ]
        ]
    )
