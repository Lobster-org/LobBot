import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from db import upsert_user, create_match, join_match, fetch_match, set_move, recent_matches_for_user

# ===== UI Builders =====

def mode_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆚 Player vs Player", callback_data="rps:mode:PVP")],
        [InlineKeyboardButton("🤖 Player vs Computer", callback_data="rps:mode:PVC")],
    ])

def rounds_keyboard(prefix: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Best of 3", callback_data=f"{prefix}:3"),
            InlineKeyboardButton("Best of 5", callback_data=f"{prefix}:5"),
            InlineKeyboardButton("Best of 7", callback_data=f"{prefix}:7")]
    ])

def join_keyboard(match_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Join Match", callback_data=f"rps:join:{match_id}")]
    ])

def move_keyboard(match_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪨 Rock", callback_data=f"rps:move:{match_id}:rock"),
            InlineKeyboardButton("📄 Paper", callback_data=f"rps:move:{match_id}:paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data=f"rps:move:{match_id}:scissors")]
    ])
    
    
def add_handlers(app: Client):
    # ===== Command =====
    @app.on_message(filters.command("rps"))
    async def rps_entry(client: Client, message: Message):
        await upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        await message.reply_text(
            "Let's play Rock–Paper–Scissors! Choose a mode:",
            reply_markup=mode_keyboard()
        )
        
    @app.on_message(filters.command("rps_history"))
    async def rps_entry(client: Client, message: Message):
        user_id = message.from_user.id
        matches = await recent_matches_for_user(user_id, limit=10)

        if not matches:
            await message.reply_text("You have no recorded matches yet.")
            return

        def uname(uid: int) -> str:
            return "🤖 Bot" if uid == 0 else str(uid)

        lines = []
        for m in matches:
            mode = m.get("mode", "PVP" if all(p["user_id"] != 0 for p in m.get("players", [])) else "PVC")
            status = m.get("status", "unknown")
            best_of = m.get("best_of", "?")
            scores = ", ".join(f"{uname(p['user_id'])}: {p['score']}" for p in m.get("players", []))
            winner = m.get("winner_user_id")
            if status == "finished":
                winner_str = "Draw" if winner is None else uname(winner)
            else:
                winner_str = "—"
            lines.append(f"• {mode} | best of {best_of} | status: {status} | winner: {winner_str}\n  Scores: {scores}")

        text = "Here are your last 10 matches:\n\n" + "\n".join(lines)
        # keep under Telegram's 4096 char limit
        if len(text) > 4000:
            text = text[:3990] + "…"
        await message.reply_text(text)

    # ===== Callback: pick mode =====

    @app.on_callback_query(filters.regex(r"^rps:mode:(PVP|PVC)$"))
    async def rps_pick_mode(_, cq: CallbackQuery):
        mode = cq.data.split(":")[-1]
        await cq.message.edit_text(
            f"Mode: **{mode}** Now choose the number of rounds (best of):",
            reply_markup=rounds_keyboard(f"rps:rounds:{mode}")
        )
        await cq.answer()

    # ===== Callback: pick rounds =====

    @app.on_callback_query(filters.regex(r"^rps:rounds:(PVP|PVC):([357])$"))
    async def rps_pick_rounds(client: Client, cq: CallbackQuery):
        _, _, mode, best_of = cq.data.split(":")
        best_of = int(best_of)
        chat_id = cq.message.chat.id
        user = cq.from_user
        await upsert_user(user.id, user.username, user.first_name)

        match_id = await create_match(chat_id, user.id, mode, best_of)

        if mode == "PVP":
            await cq.message.edit_text(
                f"🎮 RPS PvP match created by **{user.first_name}** (best of {best_of})."
                f"Waiting for an opponent to join…",
                reply_markup=join_keyboard(match_id)
            )
        else:
            # PVC starts immediately; player vs bot (user_id=0)
            await cq.message.edit_text(
                f"🤖 RPS PvC started (best of {best_of}). Your move:",
                reply_markup=move_keyboard(match_id)
            )
        await cq.answer()

    # ===== Callback: join PVP =====

    @app.on_callback_query(filters.regex(r"^rps:join:([a-f0-9]{24})$"))
    async def rps_join(_, cq: CallbackQuery):
        match_id = cq.data.split(":")[-1]
        ok = await join_match(match_id, cq.from_user.id)
        if not ok:
            await cq.answer("Cannot join this match.", show_alert=True)
            return
        m = await fetch_match(match_id)
        p1_id = m["players"][0]["user_id"]
        p2_id = m["players"][1]["user_id"]
        await cq.message.edit_text(
            f"✅ Opponent joined! Players: [{p1_id}] vs [{p2_id}]"
            f"Round {m['current_round']}: choose your moves.",
            reply_markup=move_keyboard(match_id)
        )
        await cq.answer("Joined!")

    @app.on_callback_query(filters.regex(r"^rps:move:([a-f0-9]{24}):(rock|paper|scissors)$"))
    async def rps_move(_, cq: CallbackQuery):
        _, _, match_id, move = cq.data.split(":")
        user_id = cq.from_user.id

        # For PVC, fill bot move randomly after user's move
        m = await fetch_match(match_id)
        if not m:
            await cq.answer("Match not found.", show_alert=True)
            return
        if m["status"] != "active":
            await cq.answer("Match is not active.", show_alert=True)
            return

        # Validate that user is part of the match (or human in PVC)
        if m["mode"] == "PVC":
            human_id = next((p["user_id"] for p in m["players"] if p["user_id"] != 0), None)
            if user_id != human_id:
                await cq.answer("You're not a player in this match.", show_alert=True)
                return
        else:
            if not any(p["user_id"] == user_id for p in m["players"]):
                await cq.answer("You're not a player in this match.", show_alert=True)
                return

        # Human move
        res = await set_move(match_id, user_id, move)

        # If PVC and bot hasn't moved yet for this round, make bot move
        if m["mode"] == "PVC":
            latest = await fetch_match(match_id)
            round_no = latest["current_round"]
            # Determine whether bot has already moved for this round
            # Fetch round doc to inspect moves
            from motor.motor_asyncio import AsyncIOMotorClient  # lightweight import here
            import os
            from bson import ObjectId
            client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            db = client[os.environ.get("DB_NAME", "lobbot")]
            rdoc = await db.rounds.find_one({"match_id": ObjectId(match_id), "round_no": round_no})
            moves = (rdoc or {}).get("moves", {})
            if "0" not in moves:
                bot_move = random.choice(["rock", "paper", "scissors"])
                res = await set_move(match_id, 0, bot_move)

        # Render state
        await render_state(cq, res)


    # ===== Rendering =====
    async def render_state(cq: CallbackQuery, res: dict):
        if "error" in res:
            await cq.answer(res["error"], show_alert=True)
            return
        m = res["match"]
        best_of = m["best_of"]
        target = m["target_wins"]
        scores = {p["user_id"]: p["score"] for p in m["players"]}
        round_no = res["round_no"]

        if res.get("is_complete_round"):
            # show round result
            r_moves = res["moves"]
            # Build readable names
            def uname(uid: int):
                return "🤖 Bot" if uid == 0 else f"{uid}"
            players = [p["user_id"] for p in m["players"]]
            a, b = players[0], players[1]
            mv_a = r_moves[str(a)]
            mv_b = r_moves[str(b)]
            # decide winner of round
            if mv_a == mv_b:
                rr = f"Round {round_no}: Draw. Both chose **{mv_a}**."
            else:
                # who got the point? compare scores diff? simpler: recompute
                def beats(x,y):
                    return (x == "rock" and y == "scissors") or (x == "paper" and y == "rock") or (x == "scissors" and y == "paper")
                if beats(mv_a, mv_b):
                    rr = f"Round {round_no}: **{uname(a)}** wins ({mv_a} vs {mv_b})."
                else:
                    rr = f"Round {round_no}: **{uname(b)}** wins ({mv_b} vs {mv_a})."

            if m["status"] == "finished":
                # find winner_user_id (may be None if last round draw then tiebreak shouldn't happen with best-of odd)
                winner = m.get("winner_user_id")
                if winner is None:
                    header = "Game over! It's a draw."
                else:
                    header = f"🏆 Game over! Winner: **{winner}**"
                text = (
                    f"{header}"
                    f"{rr}"
                    f"Scoreboard (first to {target} wins):"
                    + "\n".join([f"- {uname(p['user_id'])}: {p['score']}" for p in m["players"]])
                )
                await cq.message.edit_text(text)
                await cq.answer()
                return
            else:
                # Continue to next round
                text = (
                    f"{rr}\n\n"
                    f"Scoreboard (first to {target} wins):\n"
                    + "\n".join([f"- {uname(p['user_id'])}: {p['score']}" for p in m["players"]])
                    + f"\n\nRound {m['current_round']}: choose your moves."
                )
                await cq.message.edit_text(text, reply_markup=move_keyboard(m["_id"]))
                await cq.answer("Next round!")
                return
        else:
            # Wait for the other player
            await cq.answer("Move locked. Waiting for the other player…", show_alert=False)