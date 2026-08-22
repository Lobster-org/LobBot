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
        "warn",
        "/warn @user <reason>",
        "Add a persistent warning for a member in this group. Reply targets are supported.",
    ),
    CommandHelp(
        "warnings",
        "/warnings @user",
        "List a member's active manual and automated moderation warnings.",
    ),
    CommandHelp(
        "warnremove",
        "/warnremove <id>",
        "Remove one active warning using the ID displayed by /warnings.",
    ),
    CommandHelp(
        "automod",
        "/automod [status|on|off]",
        "Configure flood, repeated-message, link, excessive-caps, and blocked-word filters for this group.",
    ),
    CommandHelp(
        "mute",
        "/mute @user <10s|5m|2h|7d> [reason]",
        "Temporarily prevent a member from sending messages. Replying to the member is also supported.",
    ),
    CommandHelp(
        "unmute",
        "/unmute @user",
        "Restore a muted member's group messaging permissions. Reply targets are supported.",
    ),
    CommandHelp(
        "ban",
        "/ban @user [reason]",
        "Ban a member from the group and record the moderation action. Reply targets are supported.",
    ),
    CommandHelp(
        "kick",
        "/kick @user",
        "Remove a member without permanently banning them. You can optionally add a reason or reply to the member's message.",
    ),
    CommandHelp(
        "unban",
        "/unban @user",
        "Remove a Telegram ban and close the member's active LobBot ban record.",
    ),
    CommandHelp(
        "banned",
        "/banned",
        "List active LobBot ban records and unban users with inline buttons.",
    ),
    CommandHelp(
        "purge",
        "/purge <amount> or reply with /purge",
        "Delete recent messages in bulk. With a reply, deletion starts at that message and ends at /purge. Maximum: 10,000.",
    ),
    CommandHelp("rules", "/rules", "Show the rules configured for the current group."),
    CommandHelp("community", "/community", "Show welcome, goodbye, rules, verification, and service-message settings."),
    CommandHelp("welcome", "/welcome on|off", "Enable or disable welcome messages for new members."),
    CommandHelp("setwelcome", "/setwelcome <message>", "Set the welcome template. Supports {mention}, {name}, {first_name}, {username}, {group}, and {member_count}."),
    CommandHelp("goodbye", "/goodbye on|off", "Enable or disable comical goodbye messages."),
    CommandHelp("setgoodbye", "/setgoodbye <message>", "Set the goodbye template using the community template variables."),
    CommandHelp("setrules", "/setrules <text>", "Save the current group's rules."),
    CommandHelp("clearrules", "/clearrules", "Remove the current group's configured rules."),
    CommandHelp("verification", "/verification on|off", "Require newcomers to press their personal Verify button before chatting."),
    CommandHelp("servicecleanup", "/servicecleanup on|off", "Delete Telegram join and leave service messages after community processing."),
    CommandHelp("games", "/games", "List the games available in the current group."),
    CommandHelp("cancelgame", "/cancelgame", "Cancel your active game. Either participant may cancel a multiplayer RPS match."),
    CommandHelp("coinflip", "/coinflip [heads|tails]", "Flip a coin, optionally predicting the outcome."),
    CommandHelp("guess", "/guess [number]", "Start a 1–20 number game or submit a guess. You have five attempts."),
    CommandHelp("rps", "/rps [@user]", "Play a cancellable 5, 10, or 20-round match. Multiplayer supports Normal or virtual-coin Bets mode."),
    CommandHelp("bet", "/bet <amount>", "Lock a custom virtual-coin stake into your active RPS betting match. Use the match button to go all in."),
    CommandHelp("tictactoe", "/tictactoe [@user]", "Play a cancellable 5, 10, or 20-round Tic-Tac-Toe match against LobBot or another member in one updating message."),
    CommandHelp("connect4", "/connect4 [@user]", "Play a cancellable 5, 10, or 20-round Connect 4 match against LobBot or another member in one updating message."),
    CommandHelp("hangman", "/hangman @user", "Invite a player, then privately submit a secret phrase that remains hidden until the single-message game ends."),
    CommandHelp("hangmansecret", "/hangmansecret <code> <phrase>", "Privately submit the phrase, then optionally provide a hint that appears when the guesser reaches three attempts."),
    CommandHelp("trivia", "/trivia", "Choose a category with inline buttons, then play 5, 10, or 20 fresh API-backed trivia rounds in one updating message."),
    CommandHelp("profile", "/profile", "Show your group-scoped XP, level, coins, game statistics, and daily streak."),
    CommandHelp("balance", "/balance", "Show your coin balance in this group."),
    CommandHelp("level", "/level", "Show your current level and XP."),
    CommandHelp("daily", "/daily", "Claim your approximately 24-hour coin and XP reward."),
    CommandHelp("leaderboard", "/leaderboard [xp|coins|wins]", "Show a top-ten group leaderboard. XP is the default."),
    CommandHelp("pay", "/pay @user <amount>", "Transfer group coins to another member; reply targets are also supported."),
    CommandHelp("anime", "/anime <query>", "Search AniList for anime and browse owner-scoped paginated results."),
    CommandHelp("manga", "/manga <query>", "Search AniList for manga and open detailed publication information."),
    CommandHelp("manhwa", "/manhwa <query>", "Search Korean-origin comics from AniList."),
    CommandHelp("movie", "/movie <query>", "Search TMDB for movies. Requires TMDB to be configured by the bot operator."),
    CommandHelp("tv", "/tv <query>", "Search TMDB for television series."),
    CommandHelp("ud", "/ud <word or phrase>", "Browse Urban Dictionary definitions, examples, votes, and source links."),
    CommandHelp("tr", "/tr [target] <text>", "Translate text, or reply with /tr. The default target is English."),
    CommandHelp("afk", "/afk [reason]", "Mark yourself AFK in this group. Your next normal message clears it; commands do not."),
    CommandHelp("brb", "/brb [reason]", "Mark yourself briefly away using the same group-scoped AFK tracking."),
    CommandHelp("mentions", "/mentions", "Show up to ten of the bounded missed mentions in your current AFK session."),
    CommandHelp("pat", "/pat @user or reply with /pat", "Pat another member with a randomized anime reaction GIF."),
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
