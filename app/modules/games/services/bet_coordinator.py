import asyncio
from secrets import token_hex


class BetCoordinator:
    REQUEST = "game.bet_requested"
    SETTLE = "game.bet_settlement_requested"
    RESPONSE = "game.bet_response"

    def __init__(self, events, timeout=8):
        self.events = events; self.timeout = timeout; self._pending = {}

    async def receive(self, event):
        request_id = event.payload.get("request_id")
        future = self._pending.get(request_id)
        if future and not future.done(): future.set_result(event.payload)

    async def place(self, chat_id, user_id, match_id, amount=None, all_in=False):
        return await self._request(self.REQUEST, {"chat_id": chat_id, "user_id": user_id,
            "match_id": match_id, "amount": amount, "all_in": all_in})

    async def settle(self, chat_id, match_id, bets, winner_id=None):
        return await self._request(self.SETTLE, {"chat_id": chat_id, "match_id": match_id,
            "bets": dict(bets), "winner_id": winner_id})

    async def _request(self, event_name, payload):
        request_id = token_hex(8); future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future; payload["request_id"] = request_id
        try:
            await self.events.emit(event_name, payload)
            return await asyncio.wait_for(future, self.timeout)
        except TimeoutError:
            return {"ok": False, "error": "Economy did not respond. Try again."}
        finally:
            self._pending.pop(request_id, None)

    def clear(self):
        for future in self._pending.values():
            if not future.done(): future.cancel()
        self._pending.clear()
