import logging
from app.modules.economy.config import GAME_COMPLETE_XP, GAME_WIN_COINS, GAME_WIN_XP
from app.modules.economy.events import GAME_REWARDED
from app.services.module_service import ModuleService

logger = logging.getLogger(__name__)


class EconomyListeners:
    BET_REQUEST = "game.bet_requested"
    BET_SETTLE = "game.bet_settlement_requested"
    BET_RESPONSE = "game.bet_response"
    def __init__(self, service, database=None, module_service=None, bets=None):
        self.service = service
        self.modules = module_service or ModuleService(database)
        self.bets = bets

    async def completed(self, event):
        p = event.payload; chat_id, user_id = p.get("chat_id"), p.get("user_id")
        if not chat_id or not user_id or not await self.modules.is_enabled(chat_id, "economy"): return
        settings = await self.service.settings.get(chat_id)
        if not settings["rewards_enabled"]: return
        xp = max(1, round(GAME_COMPLETE_XP * settings["xp_multiplier"]))
        await self.service.profiles.increment(chat_id, user_id, {"games_played": 1})
        await self.service.add_xp(chat_id, user_id, xp, "game_completed")

    async def won(self, event):
        p = event.payload; chat_id, user_id = p.get("chat_id"), p.get("user_id")
        if not chat_id or not user_id or not await self.modules.is_enabled(chat_id, "economy"): return
        settings = await self.service.settings.get(chat_id)
        if not settings["rewards_enabled"]: return
        xp = max(1, round(GAME_WIN_XP * settings["xp_multiplier"])); coins = max(1, round(GAME_WIN_COINS * settings["coin_multiplier"]))
        await self.service.profiles.increment(chat_id, user_id, {"games_won": 1})
        await self.service.add_xp(chat_id, user_id, xp, "game_win")
        await self.service.add_coins(chat_id, user_id, coins, "game_win")
        await self.service.events.emit(GAME_REWARDED, {
            "chat_id": chat_id, "user_id": user_id, "coins": coins,
            "game": p.get("game"), "match_id": (p.get("metadata") or {}).get("match_id"),
        })

    async def bet_requested(self, event):
        p = event.payload
        response = {"request_id": p.get("request_id"), "ok": False}
        try:
            if not await self.modules.is_enabled(p["chat_id"], "economy"):
                raise ValueError("Economy is not enabled in this group.")
            profile = await self.service.profile(p["chat_id"], p["user_id"])
            amount = profile.coins if p.get("all_in") else int(p.get("amount") or 0)
            if amount <= 0: raise ValueError("Your bet must be at least 1 coin.")
            await self.service.remove_coins(p["chat_id"], p["user_id"], amount,
                "rps_bet_escrow", "debit", {"match_id": p["match_id"]})
            try:
                await self.bets.create(p["chat_id"], p["match_id"], p["user_id"], amount)
            except Exception:
                await self.service.add_coins(p["chat_id"], p["user_id"], amount,
                    "rps_bet_escrow_rollback", "credit", {"match_id": p["match_id"]})
                raise
            response.update({"ok": True, "amount": amount})
        except Exception as error:
            response["error"] = str(error)
        await self.service.events.emit(self.BET_RESPONSE, response)

    async def bet_settlement(self, event):
        p = event.payload; response = {"request_id": p.get("request_id"), "ok": False}
        try:
            records = await self.bets.claim_match(p["match_id"], p["request_id"])
            if not records: raise ValueError("The pot was already settled or is unavailable.")
            bets = {int(record["user_id"]): int(record["amount"]) for record in records}
            winner = p.get("winner_id")
            if winner is None:
                for user_id, amount in bets.items():
                    await self.service.add_coins(p["chat_id"], user_id, amount,
                        "rps_bet_refund", "credit", {"match_id": p["match_id"]})
                response.update({"ok": True, "refunded": True, "pot": sum(bets.values())})
            else:
                pot = sum(bets.values())
                await self.service.add_coins(p["chat_id"], int(winner), pot,
                    "rps_bet_winnings", "credit", {"match_id": p["match_id"]})
                response.update({"ok": True, "winner_id": int(winner), "pot": pot})
            await self.bets.mark_settled(p["request_id"], "refunded" if winner is None else "paid")
        except Exception as error:
            if self.bets: await self.bets.release(p.get("request_id"))
            response["error"] = str(error)
        await self.service.events.emit(self.BET_RESPONSE, response)

    async def recover_unsettled_bets(self):
        if not self.bets: return 0
        await self.bets.reset_processing()
        records = await self.bets.unsettled(); recovered = 0
        for record in records:
            settlement_id = f"recovery-{record['_id']}"
            claimed = await self.bets.claim_match(record["match_id"], settlement_id)
            for item in claimed:
                await self.service.add_coins(item["chat_id"], item["user_id"], item["amount"],
                    "rps_bet_restart_refund", "credit", {"match_id": item["match_id"]})
                recovered += 1
            await self.bets.mark_settled(settlement_id, "refunded")
        return recovered
