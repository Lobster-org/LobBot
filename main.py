'''
os library - to read the environment varibales stored in system.
'''

import os 
import telebot #API implementation 
from telebot import types

BOT_TOKEN = "7161679846:AAHt4xWulza1OSvtTYaaXN58E0YO37uE4cE"

#BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

#welcome function
@bot.callback_query_handler(func=lambda call: call.data == 'start')
def send_welcome(call):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    itembtn1 = types.KeyboardButton('Option 1')
    itembtn2 = types.KeyboardButton('Option 2')
    itembtn3 = types.KeyboardButton('Option 3')

    markup.add(itembtn1,itembtn2,itembtn3)

    bot.send_message(call.message.chat.id, "Hello and welcome to (LOB)STER\nHow can I assist you today?",reply_markup = markup)

#handler for option 1
@bot.message_handler(func=lambda message: message.text == 'Option 1')
def handle_option_one(message):
    bot.reply_to(message, "You selected option 1")

#handler for option 2
@bot.message_handler(func=lambda message: message.text == 'Option 2')
def handle_option_one(message):
    bot.reply_to(message, "You selected option 2")

#handler for option 3
@bot.message_handler(func=lambda message: message.text == 'Option 3')
def handle_option_one(message):
    bot.reply_to(message, "You selected option 3")


@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "Type / to display options")


#to keep the bot running
bot.infinity_polling()