import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Format: { user_id: {mode, rounds, current_round, player_score, bot_score }}
active_games = {}

def add_handlers(app:Client):
    @app.on_message(filters.command("rps"))
    async def rps_game(client, message):
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("PvC", callback_data=f"rps_mode_pvc_{message.from_user.id}"),
                    InlineKeyboardButton("PvP", callback_data=f"rps_mode_pvp_{message.from_user.id}"),
                ]
            ]
        )
        
        await message.reply_text("Choose game mode:", reply_markup=keyboard)
        
        
    @app.on_callback_query(filters.regex(r"rps_mode_(pvc|pvp)_(\d+)"))
    async def handle_mode_selection(client, callback_query):
        mode, user_id = callback_query.data.split("_")[2:]
        
        if str(callback_query.from_user.id) != user_id:
            await callback_query.answer("You're not the one who started this game.", show_alert=True)
            return
        
        rounds_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("3 Rounds", callback_data=f"rps_rounds_{mode}_3_{user_id}"),
                    InlineKeyboardButton("5 Rounds", callback_data=f"rps_rounds_{mode}_5_{user_id}"),
                    InlineKeyboardButton("10 Rounds", callback_data=f"rps_rounds_{mode}_10_{user_id}"),
                ]
            ]
        )
        
        await callback_query.message.edit_text("How many rounds?", reply_markup=rounds_markup)
        
    @app.on_callback_query(filters.regex(r"rps_rounds_(pvc|pvp)_(\d+)_(\d+)"))
    async def handle_round_selection(client, callback_query):
        mode, rounds, user_id = callback_query.data.split("_")[2:]
        user_id = int(user_id)
        rounds = int(rounds)
        
        if callback_query.from_user.id != user_id:
            await callback_query.answer("You're not the one who started this game.", show_alert=True)
            return
        
        active_games[user_id] = {
            "mode": mode,
            "rounds": rounds,
            "current_round": 1,
            "player_score": 0,
            "bot_score": 0,
        }
        
        if mode == "pvc":
            choices_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Rock", callback_data=f"rps_play_{mode}_{rounds}_rock_{user_id}"),
                        InlineKeyboardButton("Paper", callback_data=f"rps_play_{mode}_{rounds}_paper_{user_id}"),
                        InlineKeyboardButton("Scissors", callback_data=f"rps_play_{mode}_{rounds}_scissors_{user_id}"),
                    ]
                ]
            )
            
            await callback_query.message.edit_text(
                f"Game Started: PvC Mode \nRounds: {rounds}\n\nChoose your move:",
                reply_markup=choices_markup
            )
        else:
            await callback_query.message.edit_text(
                "PvP mode coming soon (waiting for second player implementation)..."
            )
            
    @app.on_callback_query(filters.regex(r"rps_play_pvc_(\d+)_(rock|paper|scissors)_(\d+)"))
    async def handle_player_mode(client, callback_query):
        rounds, player_choice, user_id = callback_query.data.split("_")[3:]
        user_id = int(user_id)
        rounds = int(rounds)
        
        if callback_query.from_user.id != user_id:
            await callback_query.answer("You're not the one who started this game.", show_alert=True)
            return
        
        game = active_games.get(user_id)
        if not game:
            await callback_query.message.edit_text("No active game found. Start a new game with /rps.")
            return
        
        bot_choice = random.choice(["rock", "paper", "scissors"])
        
        if player_choice == bot_choice:
            result = "It's a tie!"
        elif (player_choice == "rock" and bot_choice == "scissors") or \
             (player_choice == "scissors" and bot_choice == "paper") or \
             (player_choice == "paper" and bot_choice == "rock"):
            
            result = "You win this round!"
            game["player_score"] += 1
        else:
            result = "You lose!"
            game["bot_score"] += 1
        
        current_round = game["current_round"]
        total_rounds = game["rounds"]
        game["current_round"] += 1
        
        if current_round >= total_rounds:
            winner = "You win the game!" if game["player_score"] > game["bot_score"] else \
                    "Bot wins the game!" if game["player_score"] < game["bot_score"] else \
                    "It's a draw!"
            del active_games[user_id]
        
            await callback_query.message.edit_text(
                f"Round {current_round}/{total_rounds}\n"
                f"You: {player_choice}\nBot: {bot_choice}\n\n"
                f"{result}\n\n"
                f"Final Score:\nYou: {game['player_score']} | Bot: {game['bot_score']}\n\n"
                f"{winner}"
            )
        else:
            choices_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Rock", callback_data=f"rps_play_pvc_{rounds}_rock_{user_id}"),
                        InlineKeyboardButton("Paper", callback_data=f"rps_play_pvc_{rounds}_paper_{user_id}"),
                        InlineKeyboardButton("Scissors", callback_data=f"rps_play_pvc_{rounds}_scissors_{user_id}"),
                    ]
                ]
            )
            
            await callback_query.message.edit_text(
                f"Round {current_round}/{total_rounds}\n"
                f"You: {player_choice}\nBot: {bot_choice}\n\n"
                f"{result}\n\n"
                f"Current Score:\nYou: {game['player_score']} | Bot: {game['bot_score']}\n\n"
                f"Ready for Round {current_round + 1}?",
                reply_markup=choices_markup
            )