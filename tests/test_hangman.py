from types import SimpleNamespace
import pytest

from app.core.events import EventBus
from app.modules.games.games import HangmanGame
from app.modules.games.handlers import cancel_game_callback, hangman_guess_callback, hangman_text
from app.modules.games.keyboards import hangman_hint_keyboard, hangman_setup_keyboard
from app.modules.games.registry import GameRegistry
from app.modules.games.services import GameService, GameSessionService, RewardTracker, RoundMatchService


def service():
    registry = GameRegistry(); registry.register(HangmanGame())
    return GameService(registry, GameSessionService(), EventBus(),
                       matches=RoundMatchService(), rewards=RewardTracker())

def active_match(games, secret="Hello World"):
    setup = games.matches.create_hangman_setup(-100, 1, 2, "Alice", "Bob", 99)
    return games.matches.activate_hangman(setup, secret)

def test_hangman_secret_validation_mask_and_solved_state():
    game = HangmanGame()
    assert game.normalize_secret("  Hello   World  ") == "Hello World"
    assert game.masked("Hi!", {"h"}) == "H _ !"
    assert game.solved("Hi!", {"h", "i"}) is True
    with pytest.raises(ValueError): game.normalize_secret("123")

def test_hangman_drawing_advances_with_wrong_guesses():
    game = HangmanGame()
    assert "O" not in game.drawing(0)
    assert "O" in game.drawing(1)
    assert "/|\\" in game.drawing(4)
    assert "/ \\" in game.drawing(6)
    assert game.drawing(99) == game.drawing(6)

def test_hangman_setup_keyboard_links_to_bot_private_chat():
    keyboard = hangman_setup_keyboard("abc123", 42, "LobBotExample")
    private_chat, cancel = keyboard.inline_keyboard[0]
    assert private_chat.url == "https://t.me/LobBotExample"
    assert cancel.callback_data == "games:cancel:hangmansetup:abc123:42"

def test_hint_choice_keyboard_has_yes_and_no_options():
    keyboard = hangman_hint_keyboard("abc123", 42)
    callbacks = [button.callback_data for button in keyboard.inline_keyboard[0]]
    assert callbacks == [
        "games:hangmanhint:yes:abc123:42",
        "games:hangmanhint:no:abc123:42",
    ]

def test_hangman_hint_stays_hidden_until_three_attempts_remain():
    games = service()
    setup = games.matches.create_hangman_setup(-100, 1, 2, "Alice", "Bob", 99)
    match = games.matches.activate_hangman(setup, "elephant", "It has a trunk")
    assert "It has a trunk" not in hangman_text(match)
    match.attempts_left = 3
    assert "Hint: <b>It has a trunk</b>" in hangman_text(match)

@pytest.mark.asyncio
async def test_only_invited_player_can_guess_and_message_is_edited():
    games = service(); match = active_match(games, "cat")
    edits, alerts = [], []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): alerts.append((args, kwargs))
    message = SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text)
    outsider = SimpleNamespace(data=f"games:hangman:{match.id}:c", from_user=SimpleNamespace(id=3), message=message, answer=answer)
    await hangman_guess_callback(outsider, games)
    assert alerts[-1][1]["show_alert"] is True and edits == []
    guesser = SimpleNamespace(data=f"games:hangman:{match.id}:c", from_user=SimpleNamespace(id=2), message=message, answer=answer)
    await hangman_guess_callback(guesser, games)
    assert len(edits) == 1 and "c _ _" in edits[0]

    wrong = SimpleNamespace(data=f"games:hangman:{match.id}:z", from_user=SimpleNamespace(id=2), message=message, answer=answer)
    await hangman_guess_callback(wrong, games)
    assert "  O   |" in edits[-1]
    assert "Attempts left: <b>5</b>" in edits[-1]

@pytest.mark.asyncio
async def test_winning_hangman_reveals_secret_and_emits_result():
    games = service(); match = active_match(games, "a")
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): pass
    callback = SimpleNamespace(data=f"games:hangman:{match.id}:a", from_user=SimpleNamespace(id=2),
                               message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text), answer=answer)
    await hangman_guess_callback(callback, games)
    assert "Solved" in edits[0] and "The secret was: <b>a</b>" in edits[0]
    assert games.matches.get(match.id) is None

@pytest.mark.asyncio
async def test_hangman_cancellation_reveals_secret():
    games = service(); match = active_match(games, "hidden phrase")
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): pass
    callback = SimpleNamespace(data=f"games:cancel:hangman:{match.id}", from_user=SimpleNamespace(id=1),
                               message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text), answer=answer)
    await cancel_game_callback(callback, games)
    assert "hidden phrase" in edits[0]
    assert games.matches.get(match.id) is None
