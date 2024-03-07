from telebot import TeleBot

def is_admin(bot: TeleBot, chat_id: int, user_id: int) -> bool:
    admins = bot.get_chat_administrators(chat_id)
    return any(admin.user.id == user_id for admin in admins)