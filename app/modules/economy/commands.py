from html import escape
from aiogram.filters import Command
from aiogram.types import Message

from app.modules.economy.router import router
from app.modules.economy.services.economy_service import DailyAlreadyClaimed, InsufficientBalance
from app.telegram.filters import ModuleEnabled
from app.telegram.helpers import smart_reply


@router.message(Command("profile"), ModuleEnabled("economy"))
async def profile(message: Message, economy_service):
    p = await economy_service.profile(message.chat.id, message.from_user.id)
    name = escape(message.from_user.full_name)
    await smart_reply(message, f"<b>{name}'s Profile</b>\n\nLevel: {p.level}\nXP: {p.xp:,}\nCoins: {p.coins:,}\nGames Played: {p.games_played}\nGames Won: {p.games_won}\nDaily Streak: {p.daily_streak}", parse_mode="HTML")


@router.message(Command("balance"), ModuleEnabled("economy"))
async def balance(message: Message, economy_service):
    p = await economy_service.profile(message.chat.id, message.from_user.id)
    await smart_reply(message, f"🪙 Balance: <b>{p.coins:,}</b> coins", parse_mode="HTML")


@router.message(Command("level"), ModuleEnabled("economy"))
async def level(message: Message, economy_service):
    p = await economy_service.profile(message.chat.id, message.from_user.id)
    await smart_reply(message, f"⭐ Level <b>{p.level}</b> · {p.xp:,} XP", parse_mode="HTML")


@router.message(Command("daily"), ModuleEnabled("economy"))
async def daily(message: Message, economy_service):
    try: coins, xp, streak = await economy_service.daily(message.chat.id, message.from_user.id)
    except DailyAlreadyClaimed:
        await smart_reply(message, "⏳ Your daily reward is still recharging. Try again later."); return
    except ValueError as error:
        await smart_reply(message, str(error)); return
    await smart_reply(message, f"🎁 Daily claimed: {coins} coins + {xp} XP\n🔥 Streak: {streak}")


@router.message(Command("leaderboard"), ModuleEnabled("economy"))
async def leaderboard(message: Message, economy_service):
    parts = (message.text or "").split(); metric = parts[1].lower() if len(parts) > 1 else "xp"
    try: rows, rank = await economy_service.leaderboards.get(message.chat.id, metric, message.from_user.id)
    except ValueError as error: await smart_reply(message, str(error)); return
    field = economy_service.leaderboards.FIELDS[metric]
    lines = [f"🏆 <b>{metric.upper()} Leaderboard</b>", ""]
    lines.extend(f"{i}. <code>{row['user_id']}</code> — {row.get(field, 0):,}" for i, row in enumerate(rows, 1))
    if not rows: lines.append("No rankings yet. Go play something!")
    if rank: lines.extend(["", f"Your rank: #{rank}"])
    await smart_reply(message, "\n".join(lines), parse_mode="HTML")


@router.message(Command("pay"), ModuleEnabled("economy"))
async def pay(message: Message, economy_service, permission_service):
    parts = (message.text or "").split()
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.id; amount_text = parts[1] if len(parts) > 1 else ""
    elif len(parts) >= 3:
        target = await permission_service.resolve_user_id(parts[1]); amount_text = parts[2]
    else: target = None; amount_text = ""
    try: amount = int(amount_text)
    except ValueError: amount = 0
    if not target or amount <= 0: await smart_reply(message, "Usage: /pay @user <amount> (or reply with /pay <amount>)"); return
    try: await economy_service.transfer_coins(message.chat.id, message.from_user.id, target, amount)
    except (ValueError, InsufficientBalance) as error: await smart_reply(message, f"❌ {error}"); return
    await smart_reply(message, f"✅ Sent {amount:,} coins to <code>{target}</code>.", parse_mode="HTML")
