'''
os library - to read the environment varibales stored in system.
'''

import os 
import telebot #API implementation 
import requests
from telebot import types
from PyDictionary import PyDictionary


#function imports

from functions.purge import handle_purge
from functions.help import help_command
from functions.search import search_command,search_reply, search_query
from functions.status import get_user_status
from functions.startup import send_welcome
from functions.reddit import handle_lore_command
from functions.movie import send_movie

BOT_TOKEN = "7161679846:AAHt4xWulza1OSvtTYaaXN58E0YO37uE4cE"

#BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)


keyboard = [
    [
        {"text": "status", "callback_data": "status"},
        {"text": "search", "callback_data": "/search"}
    ],
    [
        {"text": "Button 3", "url": "https://example.com"},
        {"text": "Button 4", "url": "https://example.com"}
    ]
]

# Function to send the keyboard
def send_custom_keyboard(chat_id):
    bot.send_chat_action(chat_id,'typing')
    markup = types.InlineKeyboardMarkup(row_width=2)
    for row in keyboard:
        buttons = [types.InlineKeyboardButton(text=btn["text"], callback_data=btn.get("callback_data"), url=btn.get("url")) for btn in row]
        markup.add(*buttons)
    bot.send_message(chat_id,"Your options are:",reply_markup=markup)

#welcome function
@bot.message_handler(commands=["start","hello"])
def handle_start(message):
    send_welcome(bot,message)

#handler for option 1
@bot.message_handler(func=lambda message: message.text == 'Help')
def handle_option_one(message):
    send_custom_keyboard(message.chat.id)

#handler for option 2
@bot.message_handler(func=lambda message: message.text == 'Option 2')
def handle_option_two(message):
    bot.reply_to(message, "You selected option 2")

#handler for option 3
@bot.message_handler(func=lambda message: message.text == 'Option 3')
def handle_option_three(message):
    bot.reply_to(message, "You selected option 3")

# Handler for callback queries
@bot.callback_query_handler(func=lambda call: call.data == "/search")
def handle_search_callback(call):
    bot.send_message(call.message.chat.id,"Type in what you would like to search")
    bot.register_next_step_handler(call.message, handle_search_input_from_callback)

def handle_search_input_from_callback(message):
    search = message.text
    bot.send_message(message.chat.id,f"searching for: {search}")
    search_query(bot,message)


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
    
#reddit post handler
@bot.message_handler(commands = ["rd"])
def post(message):
    parts = message.text.split()
    if len(parts)>1:
        subreddit_name = parts[1]
        handle_lore_command(bot,message,subreddit_name)
    else:
        handle_lore_command(bot, message)

@bot.message_handler(commands=["movie"])
def handle_movie(message):
    send_movie(bot, message)
    
bot.infinity_polling()