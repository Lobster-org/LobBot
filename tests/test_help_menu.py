from app.modules.help.help import COMMANDS_BY_NAME
from app.modules.help.keyboards import (
    COMMANDS_PER_PAGE,
    help_keyboard,
    help_page_count,
)


def test_help_catalog_contains_registered_commands():
    expected = {
        "start",
        "help",
        "modules",
        "enable",
        "disable",
        "role",
        "unrole",
        "play",
        "queue",
        "remove",
        "pause",
        "resume",
        "skip",
        "stop",
    }

    assert set(COMMANDS_BY_NAME) == expected


def test_help_keyboard_is_five_by_three():
    keyboard = help_keyboard(0)

    assert len(keyboard.inline_keyboard) == 5
    assert all(
        len(row) == 3
        for row in keyboard.inline_keyboard
    )
    assert sum(
        len(row)
        for row in keyboard.inline_keyboard[:-1]
    ) == COMMANDS_PER_PAGE


def test_help_navigation_wraps_between_pages():
    assert help_page_count() == 2

    first_page = help_keyboard(0)
    last_page = help_keyboard(1)

    assert first_page.inline_keyboard[-1][0].callback_data == (
        "help:page:1"
    )
    assert last_page.inline_keyboard[-1][2].callback_data == (
        "help:page:0"
    )
    assert first_page.inline_keyboard[-1][1].callback_data == (
        "help:start"
    )
