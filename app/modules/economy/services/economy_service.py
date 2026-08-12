import logging
from datetime import datetime, timedelta, timezone

from app.modules.economy.config import DAILY_BASE_COINS, DAILY_MAX_STREAK_BONUS_DAYS, DAILY_PERIOD_SECONDS, DAILY_STREAK_BONUS, DAILY_STREAK_GRACE_SECONDS, DAILY_XP
from app.modules.economy.events import COINS_CHANGED, DAILY_CLAIMED, TRANSFER_COMPLETED
from app.modules.economy.models.transaction import EconomyTransaction
from app.modules.economy.services.achievement_service import AchievementService
from app.modules.economy.services.leaderboard_service import LeaderboardService
from app.modules.economy.services.xp_service import XPService

logger = logging.getLogger(__name__)


class InsufficientBalance(ValueError): pass
class DailyAlreadyClaimed(ValueError): pass


class EconomyService:
    def __init__(self, profiles, transactions, settings, events):
        self.profiles, self.transactions, self.settings, self.events = profiles, transactions, settings, events
        self.xp = XPService(profiles, events); self.achievements = AchievementService(profiles, events)
        self.leaderboards = LeaderboardService(profiles)

    async def profile(self, chat_id, user_id): return await self.profiles.get(chat_id, user_id)
    async def add_xp(self, chat_id, user_id, amount, reason):
        result = await self.xp.add_xp(chat_id, user_id, amount, reason)
        await self.achievements.evaluate(chat_id, user_id)
        return result

    async def add_coins(self, chat_id, user_id, amount, reason, transaction_type="credit", metadata=None):
        if amount <= 0: raise ValueError("Coin amount must be positive")
        doc = await self.profiles.increment(chat_id, user_id, {"coins": amount})
        await self.transactions.record(EconomyTransaction(chat_id, user_id, transaction_type, amount, reason, metadata or {}))
        await self.events.emit(COINS_CHANGED, {"chat_id": chat_id, "user_id": user_id, "amount": amount, "balance": doc["coins"], "reason": reason})
        await self.achievements.evaluate(chat_id, user_id)
        return doc["coins"]

    async def remove_coins(self, chat_id, user_id, amount, reason, transaction_type="debit", metadata=None):
        if amount <= 0: raise ValueError("Coin amount must be positive")
        doc = await self.profiles.debit(chat_id, user_id, amount)
        if not doc: raise InsufficientBalance("Insufficient balance")
        await self.transactions.record(EconomyTransaction(chat_id, user_id, transaction_type, amount, reason, metadata or {}))
        await self.events.emit(COINS_CHANGED, {"chat_id": chat_id, "user_id": user_id, "amount": -amount, "balance": doc["coins"], "reason": reason})
        return doc["coins"]

    async def transfer_coins(self, chat_id, sender_id, recipient_id, amount):
        if sender_id == recipient_id: raise ValueError("Cannot transfer coins to yourself")
        if amount <= 0: raise ValueError("Transfer amount must be positive")
        await self.remove_coins(chat_id, sender_id, amount, "transfer", "transfer_out", {"recipient_id": recipient_id})
        try: await self.add_coins(chat_id, recipient_id, amount, "transfer", "transfer_in", {"sender_id": sender_id})
        except Exception:
            logger.exception("Transfer credit failed; compensating sender")
            await self.add_coins(chat_id, sender_id, amount, "transfer_refund")
            raise
        logger.info("Economy transfer: chat=%s sender=%s recipient=%s amount=%s", chat_id, sender_id, recipient_id, amount)
        await self.events.emit(TRANSFER_COMPLETED, {"chat_id": chat_id, "sender_id": sender_id, "recipient_id": recipient_id, "amount": amount})

    async def daily(self, chat_id, user_id, now=None):
        now = now or datetime.now(timezone.utc); settings = await self.settings.get(chat_id)
        if not settings["daily_enabled"]: raise ValueError("Daily rewards are disabled")
        current = await self.profile(chat_id, user_id)
        if current.last_daily_at and current.last_daily_at.tzinfo is None:
            current.last_daily_at = current.last_daily_at.replace(tzinfo=timezone.utc)
        if current.last_daily_at and now - current.last_daily_at < timedelta(seconds=DAILY_PERIOD_SECONDS): raise DailyAlreadyClaimed("Daily reward is not ready")
        streak = current.daily_streak + 1 if current.last_daily_at and now - current.last_daily_at <= timedelta(seconds=DAILY_STREAK_GRACE_SECONDS) else 1
        # Ensure the profile exists, then conditionally claim against the stored timestamp.
        await self.profiles.ensure(chat_id, user_id)
        claimed = await self.profiles.claim_daily(chat_id, user_id, now, now - timedelta(seconds=DAILY_PERIOD_SECONDS), streak)
        if not claimed: raise DailyAlreadyClaimed("Daily reward is not ready")
        coins = DAILY_BASE_COINS + DAILY_STREAK_BONUS * min(streak - 1, DAILY_MAX_STREAK_BONUS_DAYS - 1)
        await self.add_coins(chat_id, user_id, coins, "daily_reward")
        await self.add_xp(chat_id, user_id, DAILY_XP, "daily_reward")
        await self.events.emit(DAILY_CLAIMED, {"chat_id": chat_id, "user_id": user_id, "coins": coins, "xp": DAILY_XP, "streak": streak})
        return coins, DAILY_XP, streak
