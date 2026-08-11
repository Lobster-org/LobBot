from app.modules.help.help import COMMANDS_BY_NAME, command_text
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
        "mute",
        "ban",
        "unban",
        "purge",
    }

    assert set(COMMANDS_BY_NAME) == expected


def test_every_help_command_has_usage_and_description():
    assert all(
        command.usage.strip() and command.description.strip()
        for command in COMMANDS_BY_NAME.values()
    )


def test_help_details_escape_command_placeholders_for_html():
    mute_help = command_text(COMMANDS_BY_NAME["mute"])
    enable_help = command_text(COMMANDS_BY_NAME["enable"])

    assert "&lt;10s|5m|2h|7d&gt;" in mute_help
    assert "&lt;module&gt;" in enable_help
    assert "<10s|5m|2h|7d>" not in mute_help


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
