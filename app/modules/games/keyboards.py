from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def trivia_keyboard(user_id, choices, round_number=1):
    rows = [[InlineKeyboardButton(text=f"{chr(65+i)}. {choice}", callback_data=f"games:trivia:{round_number}:{i}:{user_id}")] for i, choice in enumerate(choices)]
    rows.append([InlineKeyboardButton(text="✖️ Cancel Game", callback_data=f"games:cancel:trivia:{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def rounds_keyboard(game, user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"{rounds} rounds", callback_data=f"games:rounds:{game}:{rounds}:{user_id}")
        for rounds in (5, 10, 20)
    ], [InlineKeyboardButton(text="✖️ Cancel", callback_data=f"games:cancel:setup:{game}:{user_id}")]])

def rps_match_keyboard(match_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=value.title(), callback_data=f"games:rps:{match_id}:{value}")
        for value in ("rock", "paper", "scissors")
    ], [InlineKeyboardButton(text="✖️ Cancel Game", callback_data=f"games:cancel:rps:{match_id}")]])

def rps_mode_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎮 Normal", callback_data=f"games:rpsmode:normal:{user_id}"),
        InlineKeyboardButton(text="🪙 Bets", callback_data=f"games:rpsmode:bets:{user_id}"),
    ], [InlineKeyboardButton(text="✖️ Cancel", callback_data=f"games:cancel:setup:rps:{user_id}")]])

def bet_keyboard(match_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 All In", callback_data=f"games:bet:all:{match_id}"),
    ], [InlineKeyboardButton(text="✖️ Cancel Match", callback_data=f"games:cancel:rps:{match_id}")]])

def trivia_category_keyboard(user_id):
    categories = (
        ("any", "🎲 Any"), ("general", "🧠 General"),
        ("science", "🔬 Science"), ("computers", "💻 Computers"),
        ("history", "🏛 History"), ("geography", "🌍 Geography"),
        ("sports", "⚽ Sports"), ("music", "🎵 Music"),
        ("film", "🎬 Film"), ("books", "📚 Books"),
    )
    rows = [[InlineKeyboardButton(text=label, callback_data=f"games:category:{key}:{user_id}")
             for key, label in categories[index:index + 2]]
            for index in range(0, len(categories), 2)]
    rows.append([InlineKeyboardButton(text="✖️ Cancel", callback_data=f"games:cancel:setup:trivia:{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def board_keyboard(match):
    if match.game_type == "tictactoe":
        symbols = {None: "·", "X": "❌", "O": "⭕"}
        rows = [[InlineKeyboardButton(
            text=symbols[match.board[row * 3 + col]],
            callback_data=f"games:board:tictactoe:{match.id}:{row * 3 + col}",
        ) for col in range(3)] for row in range(3)]
    else:
        rows = [[InlineKeyboardButton(
            text=str(column + 1),
            callback_data=f"games:board:connect4:{match.id}:{column}",
        ) for column in range(7)]]
    rows.append([InlineKeyboardButton(
        text="✖️ Cancel Game",
        callback_data=f"games:cancel:board:{match.id}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def hangman_keyboard(match_id, guessed=()):
    letters = "abcdefghijklmnopqrstuvwxyz"
    buttons = [InlineKeyboardButton(
        text=(letter.upper() if letter not in guessed else "·"),
        callback_data=f"games:hangman:{match_id}:{letter}",
    ) for letter in letters]
    rows = [buttons[index:index + 7] for index in range(0, len(buttons), 7)]
    rows.append([InlineKeyboardButton(
        text="✖️ Cancel Game", callback_data=f"games:cancel:hangman:{match_id}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def hangman_setup_keyboard(setup_id, creator_id, bot_username):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="💬 Open Private Chat",
            url=f"https://t.me/{bot_username}",
        ),
        InlineKeyboardButton(
            text="✖️ Cancel Setup",
            callback_data=f"games:cancel:hangmansetup:{setup_id}:{creator_id}",
        ),
    ]])

def hangman_hint_keyboard(setup_id, creator_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="💡 Yes, add a hint",
            callback_data=f"games:hangmanhint:yes:{setup_id}:{creator_id}",
        ),
        InlineKeyboardButton(
            text="▶️ No, start game",
            callback_data=f"games:hangmanhint:no:{setup_id}:{creator_id}",
        ),
    ]])
