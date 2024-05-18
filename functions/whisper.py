from telebot import TeleBot

def send_whisper(bot: TeleBot, message):
    # Split the message into username and message
    _, username, *whisper_message = message.text.split(maxsplit=2)
    
    if not (username and whisper_message):
        bot.reply_to(message, "Please provide the username and the message.")
    else:
        # Join the whisper message back together if it contains spaces
        whisper_message = ' '.join(whisper_message)
        # Find the user ID using the username
        user_id = find_user_id_by_username(bot, message, username)
        if user_id:
            bot.send_message(user_id, f"You received a whisper from {message.from_user.username}: {whisper_message}")
            bot.reply_to(message, "Whisper sent successfully.")
        else:
            bot.reply_to(message, f"User {username} not found.")


def find_user_id_by_username(bot: TeleBot, message, username):
    username = username.lstrip('@')
    group_id = get_group_id(message)
    print(username)
    members = bot.get_chat_administrators(group_id)
    for member in members:
        print(member)
        if member.user.username == username:
            return member.user.id
    
    return None

def get_group_id(message):
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        return message.chat.id
    else:
        return None
