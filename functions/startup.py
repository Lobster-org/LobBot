from telebot import TeleBot
# from telebot import types

def send_welcome(bot:TeleBot,message):
    # markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    # itembtn1 = types.KeyboardButton('Help')
    # itembtn2 = types.KeyboardButton('Option 2')
    # itembtn3 = types.KeyboardButton('Option 3')

    # markup.add(itembtn1,itembtn2,itembtn3)

    bot.reply_to(message, "Hello and welcome to (LOB)-Bot\nHow can I assist you today?")