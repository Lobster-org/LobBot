from dataclasses import dataclass


@dataclass(frozen=True)
class Connect4Game:
    name: str = "connect4"
    command: str = "connect4"
    description: str = "Drop discs in a round-based 7×6 match."

    @staticmethod
    def new_board(): return [[None for _ in range(7)] for _ in range(6)]

    @staticmethod
    def move(board, column, symbol):
        if column not in range(7): raise ValueError("Invalid column")
        for row in range(5, -1, -1):
            if board[row][column] is None:
                board[row][column] = symbol; return row
        raise ValueError("That column is full")

    @staticmethod
    def winner(board):
        for row in range(6):
            for col in range(7):
                symbol = board[row][col]
                if not symbol: continue
                for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    if all(0 <= row + dr*i < 6 and 0 <= col + dc*i < 7
                           and board[row + dr*i][col + dc*i] == symbol for i in range(4)):
                        return symbol
        return "draw" if all(cell for row in board for cell in row) else None
