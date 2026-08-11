from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class CommandHelp:
    name: str
    usage: str
    description: str


COMMANDS = (
    CommandHelp(
        "start",
        "/start",
        "Show a short introduction to LobBot and open the main menu.",
    ),
    CommandHelp(
        "help",
        "/help",
        "Open this paginated command browser. Select any command for usage details.",
    ),
    CommandHelp(
        "modules",
        "/modules",
        "List every LobBot module and show whether it is enabled in the current group.",
    ),
    CommandHelp(
        "enable",
        "/enable <module>",
        "Enable a non-core module in the current group. Requires module-management permission.",
    ),
    CommandHelp(
        "disable",
        "/disable <module>",
        "Disable a non-core module in the current group. Requires module-management permission.",
    ),
    CommandHelp(
        "role",
        "/role @user moderator",
        "Assign LobBot's custom moderator role. You can also reply to the member's message.",
    ),
    CommandHelp(
        "unrole",
        "/unrole @user",
        "Remove a member's custom LobBot role. You can also reply to their message.",
    ),
    CommandHelp(
        "play",
        "/play <song name or URL>",
        "Search for music, choose a result, download or reuse its cache, and add it to the group queue.",
    ),
    CommandHelp(
        "queue",
        "/queue",
        "Show the currently playing track and every track waiting in this group's queue.",
    ),
    CommandHelp(
        "remove",
        "/remove <position>",
        "Remove a waiting track by the position displayed in /queue.",
    ),
    CommandHelp(
        "pause",
        "/pause",
        "Pause the current voice-chat track without clearing the queue.",
    ),
    CommandHelp(
        "resume",
        "/resume",
        "Resume the currently paused voice-chat track.",
    ),
    CommandHelp(
        "skip",
        "/skip",
        "Stop the current track and immediately begin the next queued track.",
    ),
    CommandHelp(
        "stop",
        "/stop",
        "Stop voice playback, leave the call, and clear this group's music queue.",
    ),
    CommandHelp(
        "mute",
        "/mute @user <10s|5m|2h|7d> [reason]",
        "Temporarily prevent a member from sending messages. Replying to the member is also supported.",
    ),
    CommandHelp(
        "ban",
        "/ban @user [reason]",
        "Ban a member from the group and record the moderation action. Reply targets are supported.",
    ),
    CommandHelp(
        "unban",
        "/unban @user",
        "Remove a Telegram ban and close the member's active LobBot ban record.",
    ),
    CommandHelp(
        "purge",
        "/purge <amount> or reply with /purge",
        "Delete recent messages in bulk. With a reply, deletion starts at that message and ends at /purge. Maximum: 10,000.",
    ),
)


COMMANDS_BY_NAME = {
    command.name: command
    for command in COMMANDS
}


def help_text(page: int, page_count: int) -> str:
    return (
        "<b>LobBot Commands</b>\n\n"
        "Choose a command below to see its usage and description.\n"
        f"Page <b>{page + 1}</b> of <b>{page_count}</b>."
    )


def command_text(command: CommandHelp) -> str:
    return (
        f"<b>{escape(command.usage)}</b>\n\n"
        f"{escape(command.description)}"
    )
