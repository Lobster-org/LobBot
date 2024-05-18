import random
from telebot import TeleBot,types

keyboard = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
keyboard.add("Rock", "Paper", "Scissors")

# Handler for /rps command
def handle_rps_command(message, bot:TeleBot,rounds:int):
    bot.reply_to(message, "Let's play Rock-Paper-Scissors! Choose your move:", reply_markup=keyboard)
    bot.user_data[message.chat.id] = {'round':1,'rounds':rounds,'wins':0,'loses':0,'draws':0}
# Handler for user's RPS choice
def handle_rps_choice(message, bot:TeleBot):
    player_choice = message.text.lower()
    computer_choice = random.choice(['rock', 'paper', 'scissors'])

    if player_choice == computer_choice:
        result = f"It's a draw! The computer also chose {computer_choice}."
        bot.user_data[message.chat.id]['draws']+=1
    elif (player_choice == 'rock' and computer_choice == 'scissors') or \
         (player_choice == 'paper' and computer_choice == 'rock') or \
         (player_choice == 'scissors' and computer_choice == 'paper'):
        result = f"You win! The computer chose {computer_choice}."
        bot.user_data[message.chat.id]['wins']+=1
    else:
        result = f"You lose! The computer chose {computer_choice}."
        bot.user_data[message.chat.id]['loses']+=1

    bot.reply_to(message, result)

    user_data = bot.user_data[message.chat.id]
    if user_data['rounds'] >= user_data['rounds']:
        game_over_message = f"Game over! Rounds played: {user_data['rounds']},\nWins:{user_data['wins']},\nLoses:{user_data[message]},\nDraws:{user_data['draws']}"
        bot.reply_to(message,game_over_message)
    else:
        user_data['round']+=1
        bot.reply_to(message,f"Round {user_data['round']}/{user_data['rounds']}. Choose your move",reply_markup = keyboard)

