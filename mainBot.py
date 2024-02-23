'''
os library - to read the environment varibales stored in system.
'''

import os 
import telebot #API implementation 
from telebot import types
from PyDictionary import PyDictionary


BOT_TOKEN = "7161679846:AAHt4xWulza1OSvtTYaaXN58E0YO37uE4cE"

#BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

# Dictionary to store command descriptions
commands = {
    "/start": "Start the bot",
    "/search": "Search for something",
    "/help": "Display available commands"
}

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

#handler for option 2
@bot.message_handler(func=lambda message: message.text == 'Option 2')
def handle_option_two(message):
    bot.reply_to(message, "You selected option 2")

#handler for option 3
@bot.message_handler(func=lambda message: message.text == 'Option 3')
def handle_option_three(message):
    bot.reply_to(message, "You selected option 3")

#test

#search command
@bot.message_handler(commands=["search"])
def search_command(message):
    bot.send_message(message.chat.id, "Please enter your search query:")

# Handler for search queries
@bot.message_handler(func=lambda message: True)
def handle_search_query(message):
    # Here you can implement your search logic
    search_query = message.text
    # Perform search based on the query
    # For demonstration purposes, just echoing back the query
    definitions = PyDictionary.meaning(search_query)
    if not definitions:
        bot.send_message(message.chat.id,"Oopsie I found nothing, better luck next time!")
    else:
        bot.send_message(message.chat.id, f"Definitions for '{search_query}':")
        for key,value in definitions.items():
            bot.send_message(message.chat.id,f"{key}:{value}")

#handler for help
@bot.message_handler(commands=["help"])
def help_command(message):
    # Generate help message with clickable commands
    help_text = "Available commands:\n"
    for command, description in commands.items():
        help_text += f"<b>{command}</b>: {description}\n"
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")
#to keep the bot running
bot.infinity_polling()