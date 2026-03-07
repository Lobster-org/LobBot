import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

DB_NAME = "rps_lobbot"

# _client = Optional[AsyncIOMotorClient] = None
# _db = None

_client = AsyncIOMotorClient(MONGO_URL, tls=False, serverSelectionTimeoutMS=20000)
_db = _client[DB_NAME]


async def _get_db():
    global _client, _db
    if _db is not None:
        return _db
    _client = AsyncIOMotorClient(MONGO_URL, uuidRepresentation="standard")
    _db = _client[DB_NAME]
    # indexes
    await _db.users.create_index("user_id", unique=True)
    await _db.matches.create_index([("chat_id", 1), ("status", 1), ("created_at", -1)])
    await _db.rounds.create_index([("match_id", 1), ("round_no", 1)], unique=True)
    return _db

# --- Users ---
async def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    db = await _get_db()
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "updated_at": now
        },
         "$setOnInsert": {"created_at": now}},
        upsert=True
    )


# --- Matches ---
# status: waiting | active | finished
# mode: PVC | PVP
# players: [{user_id, score}] (PVC has bot user_id=0)

async def create_match(chat_id: int, creator_id: int, mode: str, best_of: int) -> str:
    db = await _get_db()
    now = datetime.now(timezone.utc)
    target_wins = best_of // 2 + 1
    players = [{"user_id": creator_id, "score": 0}]
    if mode == "PVC":
        players.append({"user_id": 0, "score": 0})  # bot id 0
        status = "active"
    else:
        status = "waiting"
    doc = {
        "chat_id": chat_id,
        "mode": mode,
        "status": status,
        "best_of": best_of,
        "target_wins": target_wins,
        "current_round": 1,
        "players": players,
        "winner_user_id": None,
        "created_at": now,
        "updated_at": now
    }
    res = await db.matches.insert_one(doc)
    return str(res.inserted_id)

async def join_match(match_id: str, joiner_user_id: int) -> bool:
    db = await _get_db()
    m = await db.matches.find_one({"_id": ObjectId(match_id)})
    if not m or m["status"] != "waiting":
        return False
    if any(p["user_id"] == joiner_user_id for p in m["players"]):
        return False
    m["players"].append({"user_id": joiner_user_id, "score": 0})
    await db.matches.update_one(
        {"_id": m["_id"]},
        {"$set": {"players": m["players"], "status": "active", "updated_at": datetime.now(timezone.utc)}}
    )
    return True

async def fetch_match(match_id: str) -> Optional[Dict[str, Any]]:
    db = await _get_db()
    m = await db.matches.find_one({"_id": ObjectId(match_id)})
    if m:
        m["_id"] = str(m["_id"])
    return m


# --- Rounds / moves ---
# rounds documents record both players' moves per round
# moves: { "<user_id>": "rock|paper|scissors" }

def _beats(a: str, b: str) -> bool:
    return (a == "rock" and b == "scissors") or (a == "paper" and b == "rock") or (a == "scissors" and b == "paper")

async def _finalize_round_and_update_match(db, match: Dict[str, Any], round_no: int, moves: Dict[str, str]) -> Dict[str, Any]:
    # Determine round winner
    users = [str(p["user_id"]) for p in match["players"]]
    move_vals = [moves.get(uid) for uid in users]
    result = {"winner_user_id": None, "is_draw": False}

    if move_vals[0] == move_vals[1]:
        result["is_draw"] = True
    else:
        if _beats(move_vals[0], move_vals[1]):
            result["winner_user_id"] = int(users[0])
        else:
            result["winner_user_id"] = int(users[1])

    # Persist round
    await db.rounds.update_one(
        {"match_id": ObjectId(match["_id"]), "round_no": round_no},
        {"$set": {
            "match_id": ObjectId(match["_id"]),
            "round_no": round_no,
            "moves": moves,
            "result": result,
            "decided_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )

    # Update match scores and state
    incs = {}
    winner_user_id = None
    finished = False
    next_round = match["current_round"]
    if not result["is_draw"] and result["winner_user_id"] is not None:
        winner_user_id = result["winner_user_id"]
        # bump that player's score
        field = "players.$[w].score"
        incs[field] = 1

    # apply score inc
    array_filters = [{"w.user_id": winner_user_id}] if winner_user_id is not None else []
    if incs:
        updated = await db.matches.find_one_and_update(
            {"_id": ObjectId(match["_id"])},
            {"$inc": incs, "$set": {"updated_at": datetime.now(timezone.utc)}},
            array_filters=array_filters,
            return_document=True
        )
        match = updated or match

    # reload to compute if finished
    match = await db.matches.find_one({"_id": ObjectId(match["_id"])})
    # check finish
    for p in match["players"]:
        if p["score"] >= match["target_wins"]:
            finished = True
            break
    if finished:
        await db.matches.update_one(
            {"_id": match["_id"]},
            {"$set": {"status": "finished", "winner_user_id": winner_user_id, "updated_at": datetime.now(timezone.utc)}}
        )
    else:
        next_round = round_no + 1
        await db.matches.update_one(
            {"_id": match["_id"]},
            {"$set": {"current_round": next_round, "updated_at": datetime.now(timezone.utc)}}
        )

    match = await db.matches.find_one({"_id": ObjectId(match["_id"])})
    match["_id"] = str(match["_id"])
    return match

async def set_move(match_id: str, user_id: int, move: str) -> Dict[str, Any]:
    db = await _get_db()
    match = await fetch_match(match_id)
    if not match or match["status"] != "active":
        return {"error": "Match not active or not found."}
    round_no = match["current_round"]
    r = await db.rounds.find_one({"match_id": ObjectId(match_id), "round_no": round_no}) or {
        "match_id": ObjectId(match_id),
        "round_no": round_no,
        "moves": {},
    }
    moves = r.get("moves", {})
    moves[str(user_id)] = move

    # Upsert partial move
    await db.rounds.update_one(
        {"match_id": ObjectId(match_id), "round_no": round_no},
        {"$set": {"moves": moves}},
        upsert=True
    )

    # If both have moved, finalize the round
    player_ids = [str(p["user_id"]) for p in match["players"]]
    if all(pid in moves for pid in player_ids):
        match = await _finalize_round_and_update_match(db, match, round_no, moves)
        return {"match": match, "round_no": round_no, "moves": moves, "is_complete_round": True}

    return {"match": match, "round_no": round_no, "moves": moves, "is_complete_round": False}

# ===== Queries =====
async def recent_matches_for_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    db = await _get_db()
    cursor = db.matches.find({"players.user_id": user_id}).sort("created_at", -1).limit(limit)
    out = []
    async for m in cursor:
        m["_id"] = str(m["_id"])
        out.append(m)
        
    return out