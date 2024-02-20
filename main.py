'''
os library - to read the environment varibales stored in system.
'''

import os 
import telebot #API implementation 

BOT_TOKEN = "7161679846:AAHt4xWulza1OSvtTYaaXN58E0YO37uE4cE"

#BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

#welcome function
@bot.message_handler(commands=["start","hello"])
def send_welcome(message):
    bot.reply_to(message, "Hello and welcome to (LOB)STER\nHow can I assist you today?")



#to keep the bot running
bot.infinity_polling()