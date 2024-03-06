'''
os library - to read the environment varibales stored in system.
'''

import os 
import telebot #API implementation 
import requests
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



# Function to get the definition from Urban Dictionary
def get_urban_definition(term):
    url = f"https://api.urbandictionary.com/v0/define?term={term}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["list"]:
            #Return definitions and example if available
            defintion = data["list"][0]["definition"]
            example = data["list"][0]["example"]
            return defintion, example
    return None


#search command
@bot.message_handler(commands=["search"])

def handle_search_query(message):
    # Here you can implement your search logic
    search_query = message.text.replace('/search','',1)
    # Perform search based on the query
    # For demonstration purposes, just echoing back the query
    definitions, example = get_urban_definition(search_query)
    if not definitions:
        bot.send_message(message.chat.id,"Oopsie I found nothing, better luck next time!")
    else:
        bold_query = f'*{search_query}*'
        respone_message = f"{bold_query}:\n{definitions}"
        if example:
            respone_message += f"\n\n{example}"
        bot.send_message(message.chat.id, respone_message, parse_mode="MarkdownV2")

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