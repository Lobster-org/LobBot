class RewardTracker:
    """Receives optional Economy outcomes without importing Economy services."""
    EVENT = "economy.game_rewarded"
    def __init__(self): self._rewards = {}
    async def receive(self, event):
        payload = event.payload; match_id = payload.get("match_id")
        if match_id: self._rewards[(match_id, payload.get("user_id"))] = int(payload.get("coins", 0))
    def pop(self, match_id, user_id): return self._rewards.pop((match_id, user_id), 0)
    def clear(self): self._rewards.clear()
