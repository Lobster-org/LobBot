from dataclasses import dataclass


@dataclass(frozen=True)
class TicTacToeGame:
    name: str = "tictactoe"
    command: str = "tictactoe"
    description: str = "Play a round-based 3×3 board match."

    @staticmethod
    def new_board(): return [None] * 9

    @staticmethod
    def move(board, position, symbol):
        if position not in range(9) or board[position] is not None:
            raise ValueError("That square is unavailable")
        board[position] = symbol

    @staticmethod
    def winner(board):
        lines = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6),
                 (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))
        for a, b, c in lines:
            if board[a] and board[a] == board[b] == board[c]: return board[a]
        return "draw" if all(board) else None
