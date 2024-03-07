import time
from telebot import TeleBot
from functions.status import is_admin, is_bot_admin

def handle_purge(bot: TeleBot, message):
    if message.reply_to_message:
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id

            if is_admin(bot,chat_id, user_id) and is_bot_admin(bot,chat_id):
                start_id = message.reply_to_message.message_id
                end_id = message.message_id

                for msg_id in range(start_id+1,end_id):
                    bot.delete_message(chat_id, msg_id)
                
                bot.delete_message(chat_id,message.reply_to_message.message_id)
                bot.reply_to(message,"I make it disappear")
            else:
                bot.reply_to(message,"I am sori but you need to be an admin or make me an admin to use /purge")
        except Exception as e:
            bot.reply_to(message,f"So it no work. Here is why:{e}")
    else:
        bot.reply_to(message,"Reply to a message with /purge and watch some magic happen:)")


