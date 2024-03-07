from telebot import TeleBot

def is_admin(bot: TeleBot, chat_id: int, user_id: int) -> bool:
    admins = bot.get_chat_administrators(chat_id)
    return any(admin.user.id == user_id for admin in admins)

def is_bot_admin(bot: TeleBot, chat_id: int) -> bool:
    bot_id = bot.get_me().id
    bot_member = bot.get_chat_member(chat_id,bot_id)
    if bot_member.status in ['creator','administrator']:
        return True
    else:
        return False

def get_user_status(bot:TeleBot, chat_id:int, user_id:int)->str:
    chat_member = bot.get_chat_member(chat_id,user_id)
    if chat_member.status == 'creator':
        return "Creator"
    elif chat_member.status == 'administrator':
        return "Admin"
    else:
        return "Regular user"