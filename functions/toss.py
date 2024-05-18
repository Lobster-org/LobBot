
import random
from telebot import TeleBot

def toss(bot:TeleBot,message):
    lst = ['Heads','Tails']
    bot.reply_to(message,random.choice(lst))

def ask(bot:TeleBot,message):
    lst = ['Yes','No','Maybe']
    question = ' '.join(message.text.split()[1:])
    if len(question) >= 1:
        bot.reply_to(message, random.choice(lst))
    else:
        bot.reply_to(message,"Please use /ask <question> format")