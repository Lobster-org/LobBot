import requests
from telebot import TeleBot
from telebot.types import Message


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
    return None, None

def search_command(bot: TeleBot,message):
    # Here you can implement your search logic
    search_query = " ".join(message.text.split()[1:])
    # Perform search based on the query
    definitions, example = get_urban_definition(search_query)
    if not definitions:
        bot.send_message(message.chat.id, "Oopsie I found nothing, better luck next time!")
    else:
        respone_message = f"{search_query}:\n{definitions}"
        if example:
            respone_message += f"\n\n{example}"
        bot.send_message(message.chat.id, respone_message)

def search_reply(bot: TeleBot, message):
    reply_message = message.reply_to_message
    if reply_message:
        search_word = message.reply_to_message.text.strip()
        definition,example = get_urban_definition(search_word)
        if definition is None:
            bot.reply_to(message,"Oopsie I found nothing, better luck next time!")
        else:
            respone_message = f"{search_word}:\n{definition}"
            if example:
                respone_message += f"\n\n{example}"
            bot.send_message(message.chat.id, respone_message)
    else:
        bot.send_message(message.chat.id,"Yoo stop messing around and find something to search")


def search_query(bot: TeleBot, message):
    if len(message.text.split())==1:
        modified_text = "/search " + message.text
        message.text = modified_text
        search_command(bot,message)

