from html import escape
from aiogram import BaseMiddleware, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.modules.games.keyboards import bet_keyboard, board_keyboard, hangman_hint_keyboard, hangman_keyboard, hangman_setup_keyboard, rounds_keyboard, rps_match_keyboard, rps_mode_keyboard, trivia_category_keyboard, trivia_keyboard
from app.modules.games.models.result import GameResult
from app.modules.games.router import router
from app.modules.games.services.game_service import CooldownActive
from app.telegram.filters import CallbackModuleEnabled, ModuleEnabled
from app.telegram.helpers import smart_reply


class GamesMiddleware(BaseMiddleware):
    def __init__(self, getter): self.getter = getter
    async def __call__(self, handler, event, data):
        service = self.getter()
        if service is None: raise RuntimeError("Games service is not initialized")
        data["game_service"] = service; return await handler(event, data)

async def cooldown_reply(message, operation):
    try: return await operation()
    except CooldownActive as error: await smart_reply(message, f"⏳ {error}")

@router.message(Command("games"), ModuleEnabled("games"))
async def games_command(message: Message, game_service):
    lines = ["<b>Games</b>", ""] + [f"/{g.command} — {escape(g.description)}" for g in game_service.registry.all()]
    await smart_reply(message, "\n".join(lines), parse_mode="HTML")

@router.message(Command("cancelgame"), ModuleEnabled("games"))
async def cancel_game_command(message: Message, game_service):
    removed = 0
    for game_type in ("guess", "trivia", "trivia_setup", "rps_setup", "tictactoe_setup", "connect4_setup"):
        removed += game_service.sessions.delete(
            message.chat.id, message.from_user.id, game_type
        ) is not None
    if game_service.matches:
        match = game_service.matches.for_user(message.chat.id, message.from_user.id)
        if match:
            if getattr(match, "game_type", None) == "hangman":
                game_service.matches.delete(match.id)
                await message.bot.edit_message_text(
                    chat_id=match.chat_id, message_id=match.message_id,
                    text=f"✖️ Hangman cancelled.\n\nThe secret was: <b>{escape(match.secret)}</b>",
                    parse_mode="HTML",
                )
                return
            if getattr(match, "betting", False) and match.bets:
                settlement = await game_service.bets.settle(
                    match.chat_id, match.id, match.bets, winner_id=None
                )
                if not settlement.get("ok"):
                    await smart_reply(message, "I couldn't refund the pot, so the match was not cancelled. Try again.")
                    return
            game_service.matches.delete(match.id); removed += 1
    await smart_reply(
        message,
        "✖️ Your active game was cancelled."
        if removed else "You don't have an active game to cancel.",
    )

@router.message(Command("coinflip"), ModuleEnabled("games"))
async def coinflip(message: Message, game_service):
    parts = (message.text or "").split(); prediction = parts[1].lower() if len(parts) > 1 else None
    try: result = await cooldown_reply(message, lambda: game_service.coinflip(message.chat.id, message.from_user.id, prediction))
    except ValueError: await smart_reply(message, "Usage: /coinflip [heads|tails]"); return
    if not result: return
    outcome = result.metadata["outcome"].title(); verdict = " You won! 🎉" if result.won is True else " You lost!" if result.won is False else ""
    await smart_reply(message, f"🪙 {outcome}.{verdict}")

@router.message(Command("guess"), ModuleEnabled("games"))
async def guess_command(message: Message, game_service):
    parts = (message.text or "").split()
    if len(parts) > 1:
        try: value = int(parts[1])
        except ValueError: await smart_reply(message, "Use a number from 1 to 20."); return
        result = await game_service.guess(message.chat.id, message.from_user.id, value)
        if not result: await smart_reply(message, "Start a game first with /guess."); return
        await send_guess_result(message, result); return
    try: await game_service.start_guess(message.chat.id, message.from_user.id)
    except CooldownActive as error: await smart_reply(message, f"⏳ {error}"); return
    await smart_reply(message, "🔢 I picked a number from 1–20. You have 5 attempts—send a number or use /guess 12.")

@router.message(F.text.regexp(r"^\d+$"), ModuleEnabled("games"))
async def numeric_guess(message: Message, game_service):
    result = await game_service.guess(message.chat.id, message.from_user.id, int(message.text))
    if result: await send_guess_result(message, result)

async def send_guess_result(message, result):
    status, attempts, target = result
    texts = {"low": "📈 Too low!", "high": "📉 Too high!", "correct": f"🎯 Correct in {attempts} attempt(s)!", "failed": f"💥 Out of attempts. The number was {target}."}
    await smart_reply(message, texts[status])

def player_name(user, fallback):
    if user and user.username: return f"@{user.username}"
    if user and user.full_name: return user.full_name
    return fallback

async def resolve_game_opponent(message, permission_service):
    parts = (message.text or "").split(); opponent_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        opponent_user = message.reply_to_message.from_user
        return opponent_user.id, opponent_user
    if len(parts) < 2: return None, None
    opponent_id = await permission_service.resolve_user_id(parts[1])
    if not opponent_id: return None, False
    try: opponent_user = (await message.bot.get_chat_member(message.chat.id, opponent_id)).user
    except Exception: pass
    return opponent_id, opponent_user

async def start_board_setup(message, game_service, permission_service, game_type):
    try: game_service.check_cooldown(message.chat.id, message.from_user.id, game_type)
    except CooldownActive as error: await smart_reply(message, f"⏳ {error}"); return
    opponent_id, opponent_user = await resolve_game_opponent(message, permission_service)
    if opponent_user is False:
        await smart_reply(message, "I couldn't find that user. Reply to their message instead."); return
    if opponent_id == message.from_user.id:
        await smart_reply(message, "You cannot challenge yourself. That would make the rematch awkward."); return
    opponent_name = player_name(opponent_user, "Player 2") if opponent_id else "LobBot"
    game_service.sessions.create(message.chat.id, message.from_user.id, f"{game_type}_setup", {
        "opponent_id": opponent_id, "owner_name": player_name(message.from_user, "Player 1"),
        "opponent_name": opponent_name,
    })
    title = "Tic-Tac-Toe" if game_type == "tictactoe" else "Connect 4"
    await smart_reply(message, f"🎲 <b>{title}</b> against <b>{escape(opponent_name)}</b>\nChoose the match length:",
                      parse_mode="HTML", reply_markup=rounds_keyboard(game_type, message.from_user.id))

@router.message(Command("tictactoe"), ModuleEnabled("games"))
async def tictactoe_command(message: Message, game_service, permission_service):
    await start_board_setup(message, game_service, permission_service, "tictactoe")

@router.message(Command("connect4"), ModuleEnabled("games"))
async def connect4_command(message: Message, game_service, permission_service):
    await start_board_setup(message, game_service, permission_service, "connect4")

def board_text(match, prefix=None):
    opponent_key = match.opponent_id or 0
    title = "Tic-Tac-Toe" if match.game_type == "tictactoe" else "Connect 4"
    board = ""
    if match.game_type == "connect4":
        icons = {None: "⚪", "X": "🔴", "O": "🟡"}
        board = "\n" + "\n".join("".join(icons[cell] for cell in row) for row in match.board)
    turn_name = match.owner_name if match.turn_id == match.owner_id else match.opponent_name
    header = f"🎲 <b>{title} · Round {match.round_number}/{match.rounds}</b>"
    score = f"{escape(match.owner_name)} {match.scores[match.owner_id]}–{match.scores[opponent_key]} {escape(match.opponent_name)}"
    return (f"{prefix + chr(10) + chr(10) if prefix else ''}{header}\n"
            f"Score: <b>{score}</b>{board}\n\nTurn: <b>{escape(turn_name)}</b>")

@router.callback_query(F.data.startswith("games:rounds:tictactoe:"), CallbackModuleEnabled("games"))
@router.callback_query(F.data.startswith("games:rounds:connect4:"), CallbackModuleEnabled("games"))
async def board_rounds_callback(callback: CallbackQuery, game_service):
    _, _, game_type, rounds, intended = callback.data.split(":")
    if callback.from_user.id != int(intended):
        await callback.answer("This game is not yours.", show_alert=True); return
    setup = game_service.sessions.get(callback.message.chat.id, callback.from_user.id, f"{game_type}_setup")
    if not setup: await callback.answer("This game setup expired.", show_alert=True); return
    game_service.sessions.delete(callback.message.chat.id, callback.from_user.id, f"{game_type}_setup")
    logic = game_service.registry.get(game_type)
    match = game_service.matches.create_board(
        game_type, callback.message.chat.id, callback.from_user.id,
        setup.state["opponent_id"], int(rounds), setup.state["owner_name"],
        setup.state["opponent_name"], logic.new_board(),
    )
    await game_service.started(match.chat_id, match.owner_id, game_type)
    await callback.message.edit_text(board_text(match), parse_mode="HTML", reply_markup=board_keyboard(match))
    await callback.answer()

def available_board_moves(match):
    if match.game_type == "tictactoe": return [index for index, cell in enumerate(match.board) if cell is None]
    return [column for column in range(7) if match.board[0][column] is None]

async def finish_board_round(callback, game_service, match, outcome):
    opponent_key = match.opponent_id or 0
    if outcome == "X": winner_id, winner_name = match.owner_id, match.owner_name
    elif outcome == "O": winner_id, winner_name = opponent_key, match.opponent_name
    else: winner_id, winner_name = None, "Draw"
    if winner_id is not None: match.scores[winner_id] += 1
    result = f"🏅 Round {match.round_number} winner: <b>{escape(winner_name)}</b>"
    if match.round_number < match.rounds:
        match.round_number += 1
        logic = game_service.registry.get(match.game_type); match.board = logic.new_board()
        match.turn_id = match.owner_id if match.round_number % 2 else (match.opponent_id or match.owner_id)
        await callback.message.edit_text(board_text(match, result), parse_mode="HTML", reply_markup=board_keyboard(match))
        return
    game_service.matches.delete(match.id)
    owner_score, opponent_score = match.scores[match.owner_id], match.scores[opponent_key]
    owner_won = True if owner_score > opponent_score else False if owner_score < opponent_score else None
    await game_service.finish(GameResult(match.game_type, match.chat_id, match.owner_id, owner_won,
        score=owner_score, metadata={"match_id": match.id, "rounds": match.rounds}))
    if match.opponent_id:
        await game_service.finish(GameResult(match.game_type, match.chat_id, match.opponent_id,
            None if owner_won is None else not owner_won, score=opponent_score,
            metadata={"match_id": match.id, "rounds": match.rounds}))
    owner_coins = game_service.rewards.pop(match.id, match.owner_id) if game_service.rewards else 0
    opponent_coins = game_service.rewards.pop(match.id, match.opponent_id) if match.opponent_id and game_service.rewards else 0
    await callback.message.edit_text(
        result + f"\n\n🏁 <b>Final score</b>\n{escape(match.owner_name)}: {owner_score} (+{owner_coins} coins)\n"
        f"{escape(match.opponent_name)}: {opponent_score} (+{opponent_coins} coins)", parse_mode="HTML")

@router.callback_query(F.data.startswith("games:board:"), CallbackModuleEnabled("games"))
async def board_move_callback(callback: CallbackQuery, game_service):
    _, _, game_type, match_id, move = callback.data.split(":")
    match = game_service.matches.get(match_id)
    if not match or getattr(match, "game_type", None) != game_type:
        await callback.answer("This game expired or ended.", show_alert=True); return
    allowed = {match.owner_id, match.opponent_id} - {None}
    if callback.from_user.id not in allowed:
        await callback.answer("This game is not yours.", show_alert=True); return
    if callback.from_user.id != match.turn_id:
        await callback.answer("It is not your turn.", show_alert=True); return
    logic = game_service.registry.get(game_type)
    symbol = "X" if callback.from_user.id == match.owner_id else "O"
    try: logic.move(match.board, int(move), symbol)
    except ValueError as error: await callback.answer(str(error), show_alert=True); return
    outcome = logic.winner(match.board)
    if not outcome and not match.opponent_id:
        bot_move = game_service.randomizer.choice(available_board_moves(match))
        logic.move(match.board, bot_move, "O"); outcome = logic.winner(match.board)
    if outcome:
        await finish_board_round(callback, game_service, match, outcome)
    else:
        match.turn_id = match.opponent_id if callback.from_user.id == match.owner_id else match.owner_id
        if not match.opponent_id: match.turn_id = match.owner_id
        await callback.message.edit_text(board_text(match), parse_mode="HTML", reply_markup=board_keyboard(match))
    await callback.answer()

@router.message(Command("hangman"), ModuleEnabled("games"))
async def hangman_command(message: Message, game_service, permission_service):
    opponent_id, opponent_user = await resolve_game_opponent(message, permission_service)
    if opponent_user is False or not opponent_id:
        await smart_reply(message, "Invite someone with /hangman @user or reply to their message with /hangman."); return
    if opponent_id == message.from_user.id:
        await smart_reply(message, "You cannot set a secret for yourself."); return
    creator_name = player_name(message.from_user, "Creator")
    guesser_name = player_name(opponent_user, "Player")
    pending = await smart_reply(
        message,
        f"🎭 <b>Hangman setup</b>\n"
        f"Creator: <b>{escape(creator_name)}</b>\n"
        f"Guesser: <b>{escape(guesser_name)}</b>\n\n"
        "The creator is sending the secret privately…",
        parse_mode="HTML",
    )
    setup = game_service.matches.create_hangman_setup(
        message.chat.id, message.from_user.id, opponent_id,
        creator_name, guesser_name, pending.message_id,
    )
    bot_user = await message.bot.get_me()
    await pending.edit_text(
        f"🎭 <b>Hangman setup</b>\n"
        f"Creator: <b>{escape(creator_name)}</b>\n"
        f"Guesser: <b>{escape(guesser_name)}</b>\n\n"
        f"<b>{escape(creator_name)}</b>, privately message LobBot:\n"
        f"<code>/hangmansecret {setup.id} your secret phrase</code>\n\n"
        "The phrase will never be posted in this group before the game ends.",
        parse_mode="HTML",
        reply_markup=hangman_setup_keyboard(
            setup.id, message.from_user.id, bot_user.username
        ),
    )

def hangman_text(match):
    logic_mask = " ".join(
        character if not character.isalpha() or character.lower() in match.guessed else "_"
        for character in match.secret
    )
    wrong = ", ".join(sorted(letter.upper() for letter in match.wrong)) or "None"
    drawing = game_hangman_drawing(len(match.wrong))
    hint = (
        f"\n💡 Hint: <b>{escape(match.hint)}</b>"
        if match.hint and match.attempts_left <= 3
        else ""
    )
    return (
        f"🎭 <b>Hangman</b>\n"
        f"Creator: <b>{escape(match.owner_name)}</b>\n"
        f"Guesser: <b>{escape(match.opponent_name)}</b>\n\n"
        f"<pre>{escape(drawing)}</pre>\n"
        f"<code>{escape(logic_mask)}</code>\n\n"
        f"Wrong letters: {wrong}\n"
        f"Attempts left: <b>{match.attempts_left}</b>{hint}"
    )

def game_hangman_drawing(wrong_guesses):
    from app.modules.games.games.hangman import HangmanGame
    return HangmanGame.drawing(wrong_guesses)

@router.message(Command("hangmansecret"), ModuleEnabled("games"))
async def hangman_secret_command(message: Message, game_service):
    if message.chat.type != "private":
        try: await message.delete()
        except Exception: pass
        await message.answer("For privacy, send that command directly to me in a private chat."); return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Usage: /hangmansecret <setup code> <secret phrase>"); return
    setup = game_service.matches.get_hangman_setup(parts[1], message.from_user.id)
    if not setup:
        await message.answer("That Hangman setup is invalid, expired, or belongs to someone else."); return
    try: secret = game_service.registry.get("hangman").normalize_secret(parts[2])
    except ValueError as error: await message.answer(str(error)); return
    game_service.sessions.create(
        message.from_user.id,
        message.from_user.id,
        "hangman_hint_choice",
        {"setup_id": setup.id, "secret": secret},
    )
    try: await message.delete()
    except Exception: pass
    await message.answer(
        "✅ Secret accepted. Would you like to provide a hint?\n\n"
        "The hint will appear when the player has 3 attempts left.",
        reply_markup=hangman_hint_keyboard(setup.id, message.from_user.id),
    )

async def activate_hangman_game(bot, game_service, creator_id, setup_id, secret, hint=None):
    setup = game_service.matches.get_hangman_setup(setup_id, creator_id)
    if not setup: return None
    match = game_service.matches.activate_hangman(setup, secret, hint)
    await bot.edit_message_text(
        chat_id=match.chat_id, message_id=match.message_id,
        text=hangman_text(match), parse_mode="HTML",
        reply_markup=hangman_keyboard(match.id),
    )
    await game_service.started(match.chat_id, match.opponent_id, "hangman")
    return match

@router.callback_query(F.data.startswith("games:hangmanhint:"))
async def hangman_hint_choice_callback(callback: CallbackQuery, game_service):
    _, _, choice, setup_id, intended = callback.data.split(":")
    if callback.from_user.id != int(intended):
        await callback.answer("This setup is not yours.", show_alert=True); return
    pending = game_service.sessions.get(
        callback.from_user.id, callback.from_user.id, "hangman_hint_choice"
    )
    if not pending or pending.state["setup_id"] != setup_id:
        await callback.answer("This hint setup expired.", show_alert=True); return
    if choice == "no":
        game_service.sessions.delete(
            callback.from_user.id, callback.from_user.id, "hangman_hint_choice"
        )
        match = await activate_hangman_game(
            callback.bot, game_service, callback.from_user.id,
            setup_id, pending.state["secret"],
        )
        if not match:
            await callback.answer("The group setup expired.", show_alert=True); return
        await callback.message.edit_text("✅ Game started without a hint.")
        await callback.answer(); return
    pending.state["awaiting_text"] = True
    await callback.message.edit_text(
        "💡 Send your hint as your next private message.\n"
        "Keep it helpful without giving away the answer."
    )
    await callback.answer()

@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def hangman_hint_text(message: Message, game_service):
    pending = game_service.sessions.get(
        message.from_user.id, message.from_user.id, "hangman_hint_choice"
    )
    if not pending or not pending.state.get("awaiting_text"):
        return
    hint = " ".join((message.text or "").strip().split())
    if not 2 <= len(hint) <= 120:
        await message.answer("Please send a hint between 2 and 120 characters."); return
    game_service.sessions.delete(
        message.from_user.id, message.from_user.id, "hangman_hint_choice"
    )
    match = await activate_hangman_game(
        message.bot, game_service, message.from_user.id,
        pending.state["setup_id"], pending.state["secret"], hint,
    )
    if not match:
        await message.answer("That group setup expired. Start a new Hangman game."); return
    try: await message.delete()
    except Exception: pass
    await message.answer("✅ Hint saved. The group game has started.")

@router.callback_query(F.data.startswith("games:hangman:"), CallbackModuleEnabled("games"))
async def hangman_guess_callback(callback: CallbackQuery, game_service):
    _, _, match_id, letter = callback.data.split(":")
    match = game_service.matches.get(match_id)
    if not match or getattr(match, "game_type", None) != "hangman":
        await callback.answer("This game expired or ended.", show_alert=True); return
    if callback.from_user.id != match.opponent_id:
        await callback.answer("This Hangman game is not yours to guess.", show_alert=True); return
    if letter in match.guessed:
        await callback.answer("That letter was already guessed.", show_alert=True); return
    match.guessed.add(letter)
    if letter not in match.secret.lower():
        match.wrong.add(letter); match.attempts_left -= 1
    logic = game_service.registry.get("hangman")
    won = logic.solved(match.secret, match.guessed)
    lost = match.attempts_left <= 0
    if won or lost:
        game_service.matches.delete(match.id)
        await game_service.finish(GameResult(
            "hangman", match.chat_id, match.opponent_id, won,
            metadata={"match_id": match.id},
        ))
        coins = game_service.rewards.pop(match.id, match.opponent_id) if game_service.rewards else 0
        result = "🎉 Solved!" if won else "💀 Out of attempts."
        await callback.message.edit_text(
            hangman_text(match) + f"\n\n{result}\nThe secret was: <b>{escape(match.secret)}</b>\n🪙 Coins gained: +{coins}",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            hangman_text(match), parse_mode="HTML",
            reply_markup=hangman_keyboard(match.id, match.guessed),
        )
    await callback.answer()

@router.message(Command("rps"), ModuleEnabled("games"))
async def rps_command(message: Message, game_service, permission_service):
    try: game_service.check_cooldown(message.chat.id, message.from_user.id, "rps")
    except CooldownActive as error: await smart_reply(message, f"⏳ {error}"); return
    parts = (message.text or "").split(); opponent = None; opponent_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        opponent_user = message.reply_to_message.from_user
        opponent = opponent_user.id
    elif len(parts) > 1:
        opponent = await permission_service.resolve_user_id(parts[1])
        if not opponent: await smart_reply(message, "I couldn't find that user. Reply to their message with /rps instead."); return
        try:
            opponent_user = (await message.bot.get_chat_member(message.chat.id, opponent)).user
        except Exception:
            opponent_user = None
    if opponent == message.from_user.id: await smart_reply(message, "You cannot challenge yourself. LobBot is already available for that existential crisis."); return
    def display_name(user, fallback):
        if user and user.username: return f"@{user.username}"
        if user and user.full_name: return user.full_name
        return fallback
    owner_name = display_name(message.from_user, "Player 1")
    opponent_name = display_name(opponent_user, parts[1] if len(parts) > 1 else "Player 2") if opponent else "LobBot"
    game_service.sessions.create(message.chat.id, message.from_user.id, "rps_setup", {
        "opponent_id": opponent, "owner_name": owner_name, "opponent_name": opponent_name,
    })
    invitation = f" against <b>{escape(opponent_name)}</b>" if opponent else " against LobBot"
    await smart_reply(message, f"✊ Starting RPS{invitation}. Choose the match length:", parse_mode="HTML", reply_markup=rounds_keyboard("rps", message.from_user.id))

@router.callback_query(F.data.startswith("games:rounds:rps:"), CallbackModuleEnabled("games"))
async def rps_rounds_callback(callback: CallbackQuery, game_service):
    _, _, _, rounds, intended = callback.data.split(":")
    if callback.from_user.id != int(intended): await callback.answer("This game is not yours.", show_alert=True); return
    setup = game_service.sessions.get(callback.message.chat.id, callback.from_user.id, "rps_setup")
    if not setup: await callback.answer("This invitation expired.", show_alert=True); return
    if setup.state["opponent_id"]:
        setup.state["rounds"] = int(rounds)
        await callback.message.edit_text(
            f"✊ <b>{escape(setup.state['owner_name'])}</b> vs "
            f"<b>{escape(setup.state['opponent_name'])}</b>\n\n"
            "Choose Normal mode or Bets mode.",
            parse_mode="HTML", reply_markup=rps_mode_keyboard(callback.from_user.id),
        )
        await callback.answer(); return
    game_service.sessions.delete(callback.message.chat.id, callback.from_user.id, "rps_setup")
    match = game_service.matches.create_rps(
        callback.message.chat.id, callback.from_user.id, setup.state["opponent_id"], int(rounds),
        setup.state["owner_name"], setup.state["opponent_name"],
    )
    await game_service.started(match.chat_id, match.owner_id, "rps")
    players = f"<b>{escape(match.owner_name)}</b> vs <b>{escape(match.opponent_name)}</b>"
    await callback.message.edit_text(f"✊ <b>RPS · {match.rounds} rounds</b>\n{players}\n\nRound 1: choose privately.", parse_mode="HTML", reply_markup=rps_match_keyboard(match.id))
    await callback.answer()

@router.callback_query(F.data.startswith("games:rpsmode:"), CallbackModuleEnabled("games"))
async def rps_mode_callback(callback: CallbackQuery, game_service):
    _, _, mode, intended = callback.data.split(":")
    if callback.from_user.id != int(intended):
        await callback.answer("This game is not yours.", show_alert=True); return
    setup = game_service.sessions.get(callback.message.chat.id, callback.from_user.id, "rps_setup")
    if not setup or "rounds" not in setup.state:
        await callback.answer("This game setup expired.", show_alert=True); return
    game_service.sessions.delete(callback.message.chat.id, callback.from_user.id, "rps_setup")
    betting = mode == "bets"
    match = game_service.matches.create_rps(
        callback.message.chat.id, callback.from_user.id, setup.state["opponent_id"],
        setup.state["rounds"], setup.state["owner_name"], setup.state["opponent_name"],
        betting=betting, message_id=callback.message.message_id,
    )
    if betting:
        await callback.message.edit_text(
            f"🪙 <b>RPS Betting · {match.rounds} rounds</b>\n"
            f"<b>{escape(match.owner_name)}</b> vs <b>{escape(match.opponent_name)}</b>\n\n"
            "Each player must use <code>/bet &lt;amount&gt;</code> or choose All In.\n"
            "Current pot: <b>0 coins</b>",
            parse_mode="HTML", reply_markup=bet_keyboard(match.id),
        )
    else:
        await game_service.started(match.chat_id, match.owner_id, "rps")
        await callback.message.edit_text(
            f"✊ <b>RPS · {match.rounds} rounds</b>\n"
            f"<b>{escape(match.owner_name)}</b> vs <b>{escape(match.opponent_name)}</b>\n\n"
            "Round 1: choose privately.", parse_mode="HTML",
            reply_markup=rps_match_keyboard(match.id),
        )
    await callback.answer()

async def update_bet_dashboard(bot, match, game_service):
    pot = sum(match.bets.values())
    owner_bet = match.bets.get(match.owner_id)
    opponent_bet = match.bets.get(match.opponent_id)
    lines = [f"🪙 <b>RPS Betting · {match.rounds} rounds</b>",
             f"<b>{escape(match.owner_name)}</b>: {owner_bet if owner_bet is not None else 'waiting'}",
             f"<b>{escape(match.opponent_name)}</b>: {opponent_bet if opponent_bet is not None else 'waiting'}",
             f"<b>Pot: {pot} coins</b>"]
    ready = owner_bet is not None and opponent_bet is not None
    if ready:
        lines.extend(["", "✅ Both bets are locked.", "✊ Round 1: choose privately."])
        await game_service.started(match.chat_id, match.owner_id, "rps")
    else:
        waiting = match.opponent_name if owner_bet is not None else match.owner_name
        lines.extend(["", f"⏳ Waiting for: <b>{escape(waiting)}</b>",
                      "Use <code>/bet &lt;amount&gt;</code> or choose All In."])
    await bot.edit_message_text(
        chat_id=match.chat_id, message_id=match.message_id,
        text="\n".join(lines), parse_mode="HTML",
        reply_markup=rps_match_keyboard(match.id) if ready else bet_keyboard(match.id),
    )

async def place_match_bet(match, user_id, game_service, amount=None, all_in=False):
    if user_id in match.bets: return False, "Your bet is already locked."
    response = await game_service.bets.place(match.chat_id, user_id, match.id, amount, all_in)
    if not response.get("ok"): return False, response.get("error", "Bet rejected.")
    match.bets[user_id] = int(response["amount"])
    return True, None

@router.message(Command("bet"), ModuleEnabled("games"))
async def bet_command(message: Message, game_service):
    match = game_service.matches.awaiting_bet_for_user(
        message.chat.id, message.from_user.id
    )
    if not match:
        await smart_reply(message, "You don't have an RPS match waiting for bets."); return
    parts = (message.text or "").split()
    try: amount = int(parts[1]) if len(parts) == 2 else 0
    except ValueError: amount = 0
    if amount <= 0: await smart_reply(message, "Usage: /bet <positive amount>"); return
    accepted, error = await place_match_bet(match, message.from_user.id, game_service, amount=amount)
    if not accepted: await smart_reply(message, f"❌ {error}"); return
    try: await message.delete()
    except Exception: pass
    await update_bet_dashboard(message.bot, match, game_service)

@router.callback_query(F.data.startswith("games:bet:all:"), CallbackModuleEnabled("games"))
async def all_in_callback(callback: CallbackQuery, game_service):
    match = game_service.matches.get(callback.data.rsplit(":", 1)[1])
    if not match: await callback.answer("This match expired.", show_alert=True); return
    if callback.from_user.id not in {match.owner_id, match.opponent_id}:
        await callback.answer("This game is not yours.", show_alert=True); return
    accepted, error = await place_match_bet(match, callback.from_user.id, game_service, all_in=True)
    if not accepted: await callback.answer(error, show_alert=True); return
    await update_bet_dashboard(callback.bot, match, game_service)
    await callback.answer("All-in bet locked.")

@router.callback_query(F.data.startswith("games:cancel:"), CallbackModuleEnabled("games"))
async def cancel_game_callback(callback: CallbackQuery, game_service):
    parts = callback.data.split(":")
    kind = parts[2]
    if kind == "setup":
        _, _, _, game, intended = parts
        if callback.from_user.id != int(intended):
            await callback.answer("This game is not yours.", show_alert=True); return
        removed = game_service.sessions.delete(
            callback.message.chat.id, callback.from_user.id, f"{game}_setup"
        )
        if not removed:
            await callback.answer("This game setup already expired.", show_alert=True); return
        await callback.message.edit_text("✖️ Game setup cancelled.")
        await callback.answer("Game cancelled."); return
    if kind == "trivia":
        intended = int(parts[3])
        if callback.from_user.id != intended:
            await callback.answer("This game is not yours.", show_alert=True); return
        removed = game_service.sessions.delete(callback.message.chat.id, intended, "trivia")
        if not removed:
            await callback.answer("This game already ended or expired.", show_alert=True); return
        await callback.message.edit_text("✖️ Trivia game cancelled.")
        await callback.answer("Game cancelled."); return
    if kind == "rps":
        match = game_service.matches.get(parts[3])
        if not match:
            await callback.answer("This game already ended or expired.", show_alert=True); return
        if callback.from_user.id not in {match.owner_id, match.opponent_id} - {None}:
            await callback.answer("This game is not yours.", show_alert=True); return
        if match.betting and match.bets:
            settlement = await game_service.bets.settle(
                match.chat_id, match.id, match.bets, winner_id=None
            )
            if not settlement.get("ok"):
                await callback.answer(
                    "I could not refund the pot, so the match remains active. Try again.",
                    show_alert=True,
                ); return
        game_service.matches.delete(match.id)
        cancelled_by = match.owner_name if callback.from_user.id == match.owner_id else match.opponent_name
        await callback.message.edit_text(
            f"✖️ RPS match cancelled by <b>{escape(cancelled_by)}</b>.",
            parse_mode="HTML",
        )
        await callback.answer("Game cancelled."); return
    if kind == "board":
        match = game_service.matches.get(parts[3])
        if not match:
            await callback.answer("This game already ended or expired.", show_alert=True); return
        if callback.from_user.id not in {match.owner_id, match.opponent_id} - {None}:
            await callback.answer("This game is not yours.", show_alert=True); return
        game_service.matches.delete(match.id)
        cancelled_by = match.owner_name if callback.from_user.id == match.owner_id else match.opponent_name
        await callback.message.edit_text(
            f"✖️ Match cancelled by <b>{escape(cancelled_by)}</b>.", parse_mode="HTML"
        )
        await callback.answer("Game cancelled."); return
    if kind == "hangmansetup":
        _, _, _, setup_id, intended = parts
        if callback.from_user.id != int(intended):
            await callback.answer("This game setup is not yours.", show_alert=True); return
        setup = game_service.matches.cancel_hangman_setup(setup_id, callback.from_user.id)
        if not setup:
            await callback.answer("This setup already expired.", show_alert=True); return
        await callback.message.edit_text("✖️ Hangman setup cancelled before a secret was submitted.")
        await callback.answer("Setup cancelled."); return
    if kind == "hangman":
        match = game_service.matches.get(parts[3])
        if not match:
            await callback.answer("This game already ended or expired.", show_alert=True); return
        if callback.from_user.id not in {match.owner_id, match.opponent_id}:
            await callback.answer("This game is not yours.", show_alert=True); return
        game_service.matches.delete(match.id)
        cancelled_by = match.owner_name if callback.from_user.id == match.owner_id else match.opponent_name
        await callback.message.edit_text(
            f"✖️ Hangman cancelled by <b>{escape(cancelled_by)}</b>.\n\n"
            f"The secret was: <b>{escape(match.secret)}</b>", parse_mode="HTML",
        )
        await callback.answer("Game cancelled."); return
    await callback.answer("Unknown game.", show_alert=True)

@router.callback_query(F.data.startswith("games:rps:"), CallbackModuleEnabled("games"))
async def rps_callback(callback: CallbackQuery, game_service):
    _, _, match_id, choice = callback.data.split(":")
    match = game_service.matches.get(match_id)
    if not match: await callback.answer("This game expired or was already completed.", show_alert=True); return
    if match.settlement_pending:
        await callback.answer("The pot is awaiting settlement. Please cancel to request a refund.", show_alert=True); return
    allowed = {match.owner_id, match.opponent_id} - {None}
    if callback.from_user.id not in allowed: await callback.answer("This game is not yours.", show_alert=True); return
    if match.betting and len(match.bets) < 2:
        await callback.answer("Both players must lock their bets first.", show_alert=True); return
    if callback.from_user.id in match.choices: await callback.answer("Your choice is already locked in.", show_alert=True); return
    match.choices[callback.from_user.id] = choice
    if match.opponent_id and len(match.choices) < 2:
        confirmed = match.owner_name if callback.from_user.id == match.owner_id else match.opponent_name
        waiting = match.opponent_name if callback.from_user.id == match.owner_id else match.owner_name
        await callback.message.edit_text(
            f"✊ <b>RPS · Round {match.round_number}/{match.rounds}</b>\n\n"
            f"✅ Confirmed: <b>{escape(confirmed)}</b>\n"
            f"⏳ Waiting for: <b>{escape(waiting)}</b>",
            parse_mode="HTML", reply_markup=rps_match_keyboard(match.id),
        )
        await callback.answer("Choice locked."); return
    owner_choice = match.choices[match.owner_id]
    opponent_choice = match.choices[match.opponent_id] if match.opponent_id else game_service.randomizer.choice(("rock", "paper", "scissors"))
    if owner_choice != opponent_choice:
        owner_won = (owner_choice, opponent_choice) in {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}
        winner = match.owner_id if owner_won else (match.opponent_id or 0)
        match.scores[winner] += 1
        round_winner = match.owner_name if owner_won else match.opponent_name
    else:
        round_winner = "Tie"
    opponent_key = match.opponent_id or 0
    score_text = f"{match.scores[match.owner_id]}–{match.scores[opponent_key]}"
    round_result = (
        f"Round {match.round_number}/{match.rounds}\n"
        f"<b>{escape(match.owner_name)}</b>: {owner_choice}\n"
        f"<b>{escape(match.opponent_name)}</b>: {opponent_choice}\n"
        f"🏅 Round winner: <b>{escape(round_winner)}</b>\n"
        f"Score: {score_text}"
    )
    if match.betting:
        round_result += f"\n🪙 Pot: <b>{sum(match.bets.values())} coins</b>"
    match.choices.clear()
    if match.round_number < match.rounds:
        match.round_number += 1
        await callback.message.edit_text(
            round_result
            + f"\n\n──────────\n✊ <b>Round {match.round_number}/{match.rounds}</b>"
            + "\nBoth players choose privately.",
            parse_mode="HTML",
            reply_markup=rps_match_keyboard(match.id),
        )
        await callback.answer(); return
    owner_score, opponent_score = match.scores[match.owner_id], match.scores[opponent_key]
    owner_won = True if owner_score > opponent_score else False if owner_score < opponent_score else None
    pot_summary = ""
    if match.betting:
        winner_id = match.owner_id if owner_won is True else match.opponent_id if owner_won is False else None
        settlement = await game_service.bets.settle(match.chat_id, match.id, match.bets, winner_id)
        if settlement.get("ok"):
            if winner_id is None:
                pot_summary = f"\n🪙 Pot refunded: {sum(match.bets.values())} coins"
            else:
                winner_name = match.owner_name if winner_id == match.owner_id else match.opponent_name
                pot_summary = f"\n🪙 <b>{escape(winner_name)}</b> takes the {sum(match.bets.values())}-coin pot!"
        else:
            pot_summary = "\n⚠️ Pot settlement failed; contact an administrator."
            match.settlement_pending = True
            await callback.message.edit_text(
                round_result + f"\n\n🏁 Final score: {owner_score}–{opponent_score}" + pot_summary,
                parse_mode="HTML", reply_markup=bet_keyboard(match.id),
            )
            await callback.answer(); return
    game_service.matches.delete(match.id)
    await game_service.finish(GameResult("rps", match.chat_id, match.owner_id, owner_won, score=owner_score, metadata={"match_id": match.id, "rounds": match.rounds}))
    if match.opponent_id:
        opponent_won = None if owner_won is None else not owner_won
        await game_service.finish(GameResult("rps", match.chat_id, match.opponent_id, opponent_won, score=opponent_score, metadata={"match_id": match.id, "rounds": match.rounds}))
    owner_coins = game_service.rewards.pop(match.id, match.owner_id) if game_service.rewards else 0
    opponent_coins = game_service.rewards.pop(match.id, match.opponent_id) if match.opponent_id and game_service.rewards else 0
    if match.betting:
        pot = sum(match.bets.values())
        owner_net = (pot - match.bets[match.owner_id] if owner_won is True else -match.bets[match.owner_id] if owner_won is False else 0) + owner_coins
        opponent_net = (pot - match.bets[match.opponent_id] if owner_won is False else -match.bets[match.opponent_id] if owner_won is True else 0) + opponent_coins
        money = (f"\n🪙 <b>{escape(match.owner_name)}</b>: {owner_net:+} coins"
                 f"\n🪙 <b>{escape(match.opponent_name)}</b>: {opponent_net:+} coins")
    else:
        money = f"\n🪙 <b>{escape(match.owner_name)}</b>: +{owner_coins} coins, lost 0" + (f"\n🪙 <b>{escape(match.opponent_name)}</b>: +{opponent_coins} coins, lost 0" if match.opponent_id else "\n🪙 LobBot: outside the economy, suspiciously")
    await callback.message.edit_text(round_result + f"\n\n🏁 Final score: {owner_score}–{opponent_score}" + pot_summary + money, parse_mode="HTML")
    await callback.answer()

@router.message(Command("trivia"), ModuleEnabled("games"))
async def trivia_command(message: Message, game_service):
    try: game_service.check_cooldown(message.chat.id, message.from_user.id, "trivia")
    except CooldownActive as error: await smart_reply(message, f"⏳ {error}"); return
    game_service.sessions.create(message.chat.id, message.from_user.id, "trivia_setup", {})
    await smart_reply(message, "🧠 Choose a trivia category:", reply_markup=trivia_category_keyboard(message.from_user.id))

@router.callback_query(F.data.startswith("games:category:"), CallbackModuleEnabled("games"))
async def trivia_category_callback(callback: CallbackQuery, game_service):
    _, _, category, intended = callback.data.split(":")
    if callback.from_user.id != int(intended):
        await callback.answer("This trivia game is not yours.", show_alert=True); return
    setup = game_service.sessions.get(callback.message.chat.id, callback.from_user.id, "trivia_setup")
    if not setup:
        await callback.answer("This trivia setup expired.", show_alert=True); return
    setup.state["category"] = category
    await callback.message.edit_text(
        f"🧠 Category selected: <b>{escape(category.replace('_', ' ').title())}</b>\n\n"
        "Choose the match length:",
        parse_mode="HTML", reply_markup=rounds_keyboard("trivia", callback.from_user.id),
    )
    await callback.answer()

@router.callback_query(F.data.startswith("games:rounds:trivia:"), CallbackModuleEnabled("games"))
async def trivia_rounds_callback(callback: CallbackQuery, game_service):
    _, _, _, rounds, intended = callback.data.split(":")
    if callback.from_user.id != int(intended): await callback.answer("This game is not yours.", show_alert=True); return
    setup = game_service.sessions.get(callback.message.chat.id, callback.from_user.id, "trivia_setup")
    if not setup or "category" not in setup.state: await callback.answer("Select a trivia category first.", show_alert=True); return
    game_service.sessions.delete(callback.message.chat.id, callback.from_user.id, "trivia_setup")
    await callback.message.edit_text("🔄 Fetching fresh trivia questions…")
    questions = await game_service.trivia.questions(int(rounds), setup.state["category"])
    question = questions[0]
    game_service.sessions.create(callback.message.chat.id, callback.from_user.id, "trivia", {"question": question, "questions": questions, "category": setup.state["category"], "rounds": int(rounds), "round": 1, "score": 0})
    await game_service.started(callback.message.chat.id, callback.from_user.id, "trivia")
    await callback.message.edit_text(f"🧠 <b>Trivia · Round 1/{rounds}</b>\n\n{escape(question['question'])}", parse_mode="HTML", reply_markup=trivia_keyboard(callback.from_user.id, question["choices"], 1))
    await callback.answer()

@router.callback_query(F.data.startswith("games:trivia:"), CallbackModuleEnabled("games"))
async def trivia_callback(callback: CallbackQuery, game_service):
    _, _, callback_round, choice, intended = callback.data.split(":")
    if callback.from_user.id != int(intended): await callback.answer("This trivia question is not yours.", show_alert=True); return
    session = game_service.sessions.get(callback.message.chat.id, callback.from_user.id, "trivia")
    if not session: await callback.answer("This question expired.", show_alert=True); return
    if int(callback_round) != session.state["round"]: await callback.answer("That round was already answered.", show_alert=True); return
    question = session.state["question"]; selected = int(choice); correct_index = question["answer"]
    won = game_service.registry.get("trivia").answer(question, selected)
    if won: session.state["score"] += 1
    options = []
    for index, option in enumerate(question["choices"]):
        marker = "✅" if index == correct_index else "❌"
        suffix = " ← your answer" if index == selected else ""
        options.append(f"{marker} {chr(65+index)}. {escape(option)}{suffix}")
    reveal = f"<b>Question {session.state['round']}/{session.state['rounds']}</b>\n{escape(question['question'])}\n\n" + "\n".join(options) + f"\n\n{'Correct! 🎉' if won else 'Not quite.'} Score: {session.state['score']}"
    if session.state["round"] < session.state["rounds"]:
        session.state["round"] += 1
        questions = session.state.get("questions")
        next_question = (
            questions[session.state["round"] - 1]
            if questions
            else game_service.registry.get("trivia").question(
                session.state.get("category"), game_service.randomizer.choice
            )
        )
        session.state["question"] = next_question
        await callback.message.edit_text(
            reveal
            + f"\n\n──────────\n🧠 <b>Trivia · Round {session.state['round']}/{session.state['rounds']}</b>"
            + f"\n\n{escape(next_question['question'])}",
            parse_mode="HTML",
            reply_markup=trivia_keyboard(callback.from_user.id, next_question["choices"], session.state["round"]),
        )
        await callback.answer(); return
    game_service.sessions.delete(callback.message.chat.id, callback.from_user.id, "trivia")
    match_id = f"trivia-{callback.message.chat.id}-{callback.from_user.id}-{id(session)}"
    match_won = session.state["score"] * 2 >= session.state["rounds"]
    await game_service.finish(GameResult("trivia", callback.message.chat.id, callback.from_user.id, match_won, score=session.state["score"], metadata={"match_id": match_id, "category": question["category"], "rounds": session.state["rounds"]}))
    coins = game_service.rewards.pop(match_id, callback.from_user.id) if game_service.rewards else 0
    await callback.message.edit_text(reveal + f"\n\n🏁 Final score: {session.state['score']}/{session.state['rounds']}\n🪙 Coins gained: +{coins}\nCoins lost: 0", parse_mode="HTML")
    await callback.answer()
