from types import SimpleNamespace
import pytest

from app.core.events import EventBus
from app.modules.games.games import Connect4Game, TicTacToeGame
from app.modules.games.handlers import board_move_callback, cancel_game_callback
from app.modules.games.registry import GameRegistry
from app.modules.games.services import GameService, GameSessionService, RewardTracker, RoundMatchService


class Random:
    def choice(self, values): return values[0]

def service():
    registry = GameRegistry(); registry.register(TicTacToeGame()); registry.register(Connect4Game())
    return GameService(registry, GameSessionService(), EventBus(), Random(),
                       matches=RoundMatchService(), rewards=RewardTracker())

def test_tictactoe_win_and_draw_detection():
    game = TicTacToeGame(); board = game.new_board()
    for position in (0, 1, 2): game.move(board, position, "X")
    assert game.winner(board) == "X"
    draw = ["X", "O", "X", "X", "O", "O", "O", "X", "X"]
    assert game.winner(draw) == "draw"

def test_connect4_horizontal_vertical_and_diagonal_wins():
    game = Connect4Game()
    horizontal = game.new_board()
    for column in range(4): game.move(horizontal, column, "X")
    assert game.winner(horizontal) == "X"
    vertical = game.new_board()
    for _ in range(4): game.move(vertical, 0, "O")
    assert game.winner(vertical) == "O"
    diagonal = game.new_board()
    for column, fillers in ((0, 0), (1, 1), (2, 2), (3, 3)):
        for _ in range(fillers): game.move(diagonal, column, "O")
        game.move(diagonal, column, "X")
    assert game.winner(diagonal) == "X"

@pytest.mark.asyncio
async def test_board_move_updates_one_message_and_rejects_outsider():
    games = service(); match = games.matches.create_board(
        "tictactoe", -100, 1, 2, 5, "Alice", "Bob",
        games.registry.get("tictactoe").new_board(),
    )
    edits, alerts = [], []
    async def edit_text(text, **kwargs): edits.append((text, kwargs))
    async def answer(*args, **kwargs): alerts.append((args, kwargs))
    message = SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text)
    outsider = SimpleNamespace(data=f"games:board:tictactoe:{match.id}:0", from_user=SimpleNamespace(id=3), message=message, answer=answer)
    await board_move_callback(outsider, games)
    assert alerts[-1][1]["show_alert"] is True and edits == []
    player = SimpleNamespace(data=f"games:board:tictactoe:{match.id}:0", from_user=SimpleNamespace(id=1), message=message, answer=answer)
    await board_move_callback(player, games)
    assert len(edits) == 1 and match.board[0] == "X"

@pytest.mark.asyncio
async def test_completed_board_round_resets_same_message():
    games = service(); match = games.matches.create_board(
        "tictactoe", -100, 1, 2, 5, "Alice", "Bob",
        ["X", "X", None, "O", "O", None, None, None, None],
    )
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): pass
    callback = SimpleNamespace(data=f"games:board:tictactoe:{match.id}:2", from_user=SimpleNamespace(id=1),
                               message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text), answer=answer)
    await board_move_callback(callback, games)
    assert len(edits) == 1
    assert "Round 1 winner: <b>Alice</b>" in edits[0]
    assert "Round 2/5" in edits[0]
    assert match.board == [None] * 9

@pytest.mark.asyncio
async def test_board_match_can_be_cancelled_by_participant():
    games = service(); match = games.matches.create_board(
        "connect4", -100, 1, 2, 5, "Alice", "Bob", Connect4Game.new_board(),
    )
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): pass
    callback = SimpleNamespace(data=f"games:cancel:board:{match.id}", from_user=SimpleNamespace(id=2),
                               message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text), answer=answer)
    await cancel_game_callback(callback, games)
    assert "Bob" in edits[0] and games.matches.get(match.id) is None
