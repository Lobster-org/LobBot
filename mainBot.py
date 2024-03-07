'''
os library - to read the environment varibales stored in system.
'''

import os 
import telebot #API implementation 
import requests
from telebot import types
from PyDictionary import PyDictionary
from telebot import apihelper

#function imports
from functions.status import is_admin, is_bot_admin
from functions.purge import handle_purge
from functions.help import help_command
from functions.search import search_command,search_reply
from functions.status import get_user_status

BOT_TOKEN = "7161679846:AAHt4xWulza1OSvtTYaaXN58E0YO37uE4cE"

#BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)


keyboard = [
    [
        {"text": "Button 1", "callback_data": "button_1"},
        {"text": "Button 2", "callback_data": "button_2"}
    ],
    [
        {"text": "Button 3", "url": "https://example.com"},
        {"text": "Button 4", "url": "https://example.com"}
    ]
]

#welcome function
@bot.message_handler(commands=["start","hello"])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Option 1')
    itembtn2 = types.KeyboardButton('Option 2')
    itembtn3 = types.KeyboardButton('Option 3')

    markup.add(itembtn1,itembtn2,itembtn3)

    bot.reply_to(message, "Hello and welcome to (LOB)STER\nHow can I assist you today?",reply_markup = markup)

#handler for option 1
@bot.message_handler(func=lambda message: message.text == 'Option 1')
def handle_option_one(message):
    bot.reply_to(message, "You selected option 1")
    send_custom_keyboard(message.chat.id)

#handler for option 2
@bot.message_handler(func=lambda message: message.text == 'Option 2')
def handle_option_two(message):
    bot.reply_to(message, "You selected option 2")

#handler for option 3
@bot.message_handler(func=lambda message: message.text == 'Option 3')
def handle_option_three(message):
    bot.reply_to(message, "You selected option 3")


# Function to send the keyboard
def send_custom_keyboard(chat_id):
    bot.send_chat_action(chat_id,'typing')
    markup = types.InlineKeyboardMarkup(row_width=2)
    for row in keyboard:
        buttons = [types.InlineKeyboardButton(text=btn["text"], callback_data=btn.get("callback_data"), url=btn.get("url")) for btn in row]
        markup.add(*buttons)
    bot.send_message(chat_id,"Your options are:",reply_markup=markup)

#handler for /search reply
@bot.message_handler(func=lambda message: message.text.lower() == '/search' and message.reply_to_message is not None)
def handle_search_reply(message):
    search_reply(bot,message)

# Search command
@bot.message_handler(commands=["search"])
def handle_search_query(message):
    if len(message.text.split()) == 1:
        bot.send_message(message.chat.id, "What are you trying to look up stoopid\nHere is a quick tutorial:\nuse /search word or reply on a message with /search")
    else:
        search_command(bot,message)

# Handler for /purge command
@bot.message_handler(commands=["purge"])
def handle_purge_commands(message):
    handle_purge(bot,message)

#handler for help
@bot.message_handler(commands=["help"])  
def handle_help(message):
    help_command(bot,message)

@bot.message_handler(commands = ["status"])
def get_stat(message):
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        chat_id = message.chat.id
        status = get_user_status(bot,chat_id,user_id)
        bot.reply_to(message,f"The user's status is: {status}")
    else:
        bot.reply_to(message,"Reply to a message to check user status")


#to keep the bot running
bot.infinity_polling()