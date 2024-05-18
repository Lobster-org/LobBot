from telebot import TeleBot

def help_command(bot: TeleBot,message):
    # Generate help message with clickable commands
    help_text = "Available commands:\n"

    commands = {
    "/start": "Start the bot",
    "/search": "Search for something",
    "/help": "Display available commands",
    "/purge": "Delete messages",
    "/status": "Shares the status of a user",
    "/rd" : "with rd you can get reddit post of a specific keyword",
    "/movie" : "Searches movies that are present on myflixertv.to",
    "/ask" : "Randomly will answer with a yes, no or maybe",
    "/toss" : "will do a random toss from head or tails"
    }
    
    for command, description in commands.items():
        help_text += f"<b>{command}</b>: {description}\n"
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")