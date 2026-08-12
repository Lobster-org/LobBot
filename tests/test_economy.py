from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest

from app.core.events import EventBus
from app.modules.economy.events import LEVEL_UP
from app.modules.economy.models.profile import EconomyProfile
from app.modules.economy.services.economy_service import DailyAlreadyClaimed, EconomyService, InsufficientBalance
from app.modules.economy.services.xp_service import XPService
from app.modules.economy.listeners import EconomyListeners


class Profiles:
    def __init__(self): self.items = {}
    async def ensure(self, chat, user): await self.get(chat, user)
    async def get(self, chat, user): return self.items.setdefault((chat, user), EconomyProfile(chat, user))
    async def increment(self, chat, user, values):
        p = await self.get(chat, user)
        for key, amount in values.items(): setattr(p, key, getattr(p, key) + amount)
        return vars(SimpleNamespace(**{k: getattr(p, k) for k in p.__dataclass_fields__}))
    async def debit(self, chat, user, amount):
        p = await self.get(chat, user)
        if p.coins < amount: return None
        p.coins -= amount; return {"coins": p.coins}
    async def set_level(self, chat, user, level):
        p = await self.get(chat, user)
        if level <= p.level: return False
        p.level = level; return True
    async def unlock(self, chat, user, achievement):
        p = await self.get(chat, user)
        if achievement in p.achievements: return False
        p.achievements.append(achievement); return True
    async def claim_daily(self, chat, user, now, cutoff, streak):
        p = await self.get(chat, user)
        if p.last_daily_at and p.last_daily_at > cutoff: return None
        p.last_daily_at = now; p.daily_streak = streak; return {"daily_streak": streak}
    async def leaderboard(self, chat, field, limit):
        return sorted(({"user_id": p.user_id, field: getattr(p, field)} for p in self.items.values() if p.chat_id == chat), key=lambda x: x[field], reverse=True)[:limit]
    async def rank(self, chat, user, field):
        values = sorted((getattr(p, field), p.user_id) for p in self.items.values() if p.chat_id == chat)[::-1]
        return next(i for i, (_, uid) in enumerate(values, 1) if uid == user)

class Transactions:
    def __init__(self): self.items = []
    async def record(self, item): self.items.append(item)
class Settings:
    async def get(self, chat): return {"daily_enabled": True, "rewards_enabled": True, "xp_multiplier": 1.0, "coin_multiplier": 1.0}

def economy():
    profiles = Profiles(); transactions = Transactions()
    return EconomyService(profiles, transactions, Settings(), EventBus()), profiles, transactions

def test_level_formula():
    assert XPService.calculate_level(0) == 0
    assert XPService.calculate_level(100) == 1
    assert XPService.calculate_level(400) == 2
    with pytest.raises(ValueError): XPService.calculate_level(-1)

@pytest.mark.asyncio
async def test_xp_gain_detects_level_up_and_creates_profile():
    service, profiles, _ = economy(); events = []
    async def record(event): events.append(event.payload)
    service.events.subscribe(LEVEL_UP, record)
    xp, level = await service.add_xp(-100, 1, 100, "test")
    assert (xp, level) == (100, 1) and events[0]["new_level"] == 1

@pytest.mark.asyncio
async def test_coin_credit_debit_insufficient_and_ledger():
    service, _, ledger = economy()
    assert await service.add_coins(-100, 1, 50, "test") == 50
    assert await service.remove_coins(-100, 1, 20, "test") == 30
    with pytest.raises(InsufficientBalance): await service.remove_coins(-100, 1, 31, "test")
    assert [item.type for item in ledger.items] == ["credit", "debit"]

@pytest.mark.asyncio
async def test_transfer_is_balanced_and_rejects_invalid_transfers():
    service, profiles, _ = economy(); await service.add_coins(-100, 1, 100, "seed")
    await service.transfer_coins(-100, 1, 2, 40)
    assert (await profiles.get(-100, 1)).coins == 60
    assert (await profiles.get(-100, 2)).coins == 40
    with pytest.raises(ValueError): await service.transfer_coins(-100, 1, 1, 1)

@pytest.mark.asyncio
async def test_daily_duplicate_and_streak():
    service, profiles, _ = economy(); now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    coins, xp, streak = await service.daily(-100, 1, now)
    assert (coins, xp, streak) == (50, 10, 1)
    with pytest.raises(DailyAlreadyClaimed): await service.daily(-100, 1, now + timedelta(hours=1))
    assert (await service.daily(-100, 1, now + timedelta(hours=25)))[2] == 2

@pytest.mark.asyncio
async def test_leaderboard_and_achievement_unlock():
    service, profiles, _ = economy(); await service.add_coins(-100, 1, 1000, "test"); await service.add_coins(-100, 2, 10, "test")
    rows, rank = await service.leaderboards.get(-100, "coins", 2)
    assert rows[0]["user_id"] == 1 and rank == 2
    assert "coin_1000" in (await profiles.get(-100, 1)).achievements


@pytest.mark.asyncio
async def test_game_reward_listener_awards_only_when_economy_enabled():
    service, profiles, _ = economy()
    class Modules:
        enabled = True
        async def is_enabled(self, chat, module): return self.enabled
    listener = EconomyListeners(service, module_service=Modules())
    event = SimpleNamespace(payload={"chat_id": -100, "user_id": 1, "game": "trivia"})
    await listener.completed(event); await listener.won(event)
    p = await profiles.get(-100, 1)
    assert (p.games_played, p.games_won, p.xp, p.coins) == (1, 1, 25, 25)
    listener.modules.enabled = False
    await listener.won(event)
    assert p.coins == 25


@pytest.mark.asyncio
async def test_bet_request_requires_existing_balance_and_escrows_valid_bet():
    service, profiles, _ = economy()
    class Modules:
        async def is_enabled(self, chat, module): return True
    class Bets:
        def __init__(self): self.items = []
        async def create(self, chat, match, user, amount): self.items.append((chat, match, user, amount))
    bets = Bets(); listener = EconomyListeners(service, module_service=Modules(), bets=bets)
    responses = []
    async def response(event): responses.append(event.payload)
    service.events.subscribe(listener.BET_RESPONSE, response)
    await service.add_coins(-100, 1, 50, "seed")
    await listener.bet_requested(SimpleNamespace(payload={"request_id": "a", "chat_id": -100, "user_id": 1, "match_id": "m", "amount": 60}))
    assert responses[-1]["ok"] is False
    await listener.bet_requested(SimpleNamespace(payload={"request_id": "b", "chat_id": -100, "user_id": 1, "match_id": "m", "amount": 40}))
    assert responses[-1] == {"request_id": "b", "ok": True, "amount": 40}
    assert bets.items == [(-100, "m", 1, 40)]
    assert (await profiles.get(-100, 1)).coins == 10
