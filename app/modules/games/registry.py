class GameRegistry:
    def __init__(self): self._games = {}
    def register(self, game): self._games[game.name] = game
    def get(self, name): return self._games.get(name)
    def all(self): return tuple(self._games.values())
