from dataclasses import dataclass


@dataclass(frozen=True)
class CommandHelp:
    name: str
    usage: str
    description: str


COMMANDS = (
    CommandHelp("start", "/start", "Show a short introduction to LobBot."),
    CommandHelp("help", "/help", "Browse all available commands."),
    CommandHelp("modules", "/modules", "List LobBot modules and their status."),
    CommandHelp("enable", "/enable <module>", "Enable a module in this group."),
    CommandHelp("disable", "/disable <module>", "Disable a module in this group."),
    CommandHelp("role", "/role @user moderator", "Assign a custom moderator role."),
    CommandHelp("unrole", "/unrole @user", "Remove a custom LobBot role."),
    CommandHelp("play", "/play <song>", "Search for and queue a song."),
    CommandHelp("queue", "/queue", "Show the current song queue."),
    CommandHelp("remove", "/remove <position>", "Remove a queued song."),
    CommandHelp("pause", "/pause", "Pause music playback."),
    CommandHelp("resume", "/resume", "Resume paused playback."),
    CommandHelp("skip", "/skip", "Skip the current song."),
    CommandHelp("stop", "/stop", "Stop playback and clear the queue."),
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
        f"<b>{command.usage}</b>\n\n"
        f"{command.description}"
    )
