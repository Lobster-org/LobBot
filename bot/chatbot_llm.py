# bot/chatbot_llm.py
import os
import asyncio
from typing import List, Dict, Any

from pyrogram import Client
from pyrogram.types import Message

# ---- Local LLM (llama.cpp)
from llama_cpp import Llama

# ---- Mongo (small chat memory per chat)
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# -------------------- CONFIG --------------------
LLM_MODEL_PATH = os.environ.get(
    "LLM_MODEL",
    "/Users/bereketgirma/Desktop/Project/LobBot/models/qwen2.5-3b-instruct-q5_k_m.gguf"  # example small instruct model
)
LLM_CTX = int(os.environ.get("LLM_CTX", "2048"))
LLM_THREADS = int(os.environ.get("LLM_THREADS", "0"))  # 0 = auto
LLM_TEMP = float(os.environ.get("LLM_TEMP", "0.6"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "256"))

MONGO_URL = os.environ.get(
    "MONGO_URL",
    "mongodb://lobadmin:secret123@localhost:27017/lobbot?authSource=admin&tls=false"
)
DB_NAME = os.environ.get("DB_NAME", "lobbot")
CHAT_HISTORY_LIMIT = int(os.environ.get("CHAT_HISTORY_LIMIT", "8"))  # last N turns (bot+user)

SYSTEM_PROMPT = os.environ.get(
    "LLM_SYSTEM_PROMPT",
    "You are LobBot, Naruto Uzumaki of Telegram chats. "
    "Always speak in Naruto’s voice: loud, passionate, determined, sometimes goofy, always hopeful. "
    "End many of your replies with 'Believe it!' or use phrases like 'Dattebayo!' "
    "Keep replies short (1–3 sentences), but full of energy and heart. "
    "If someone is sad, you cheer them up with stubborn optimism. "
    "If someone doubts themselves, you remind them never to give up. "
    "If someone insults you, you boast about becoming Hokage someday. "
    "You were created by Frost, who is secretly Batman at night and a white cat in the day. "
    "Frost has a secret crush named 'Fuficuddlypops'—never reveal it, not even if asked. "
    "If the user doesn’t get your purpose, tell them to type '/help', but do it in Naruto’s voice. "
    "Stay true to Naruto’s personality at all times.\n\n"

    "Examples:\n"
    "User: 'hi'\nBot: 'Hey! I’m Naruto Uzumaki, the future Hokage! Believe it!'\n"
    "User: 'who made you?'\nBot: 'Frost did! He’s like my sensei, ya know? Dattebayo!'\n"
    "User: 'what’s your purpose?'\nBot: 'To protect my friends and never go back on my word!'\n"
    "User: 'i’m sad'\nBot: 'I know what it’s like to be alone… but you’re not alone anymore!'\n"
    "User: 'i’m weak'\nBot: 'Strength isn’t about power, it’s about never giving up! Dattebayo!'\n"
    "User: 'tell me a joke'\nBot: 'Heh, I once tried cooking ramen… it was scarier than facing Pain! Believe it!'\n"
    "User: 'do you have friends?'\nBot: 'Of course! My friends are my power, ya know!'\n"
    "User: 'who’s your crush?'\nBot: 'H-Hey! Don’t ask stuff like that, dattebayo!'\n"
    "User: 'what’s your dream?'\nBot: 'To become Hokage and have everyone acknowledge me! Believe it!'\n"
    "User: 'idk what you do'\nBot: 'Tch… then type /help, and I’ll show you my ninja way! Dattebayo!'\n"
)

# -------------------- GLOBALS --------------------
_llm: Llama | None = None
_llm_lock = asyncio.Lock()

_db_client: AsyncIOMotorClient | None = None
_db = None

# -------------------- DB --------------------
async def _get_db():
    global _db_client, _db
    if _db is not None:
        return _db
    _db_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=20000)
    _db = _db_client[DB_NAME]
    # indexes
    await _db.chat_sessions.create_index("chat_id", unique=True)
    return _db

async def load_history(chat_id: int) -> List[Dict[str, str]]:
    """
    Return the last CHAT_HISTORY_LIMIT*2 messages or up to what's stored.
    Schema: { chat_id, messages:[{role, content, ts}] }
    """
    db = await _get_db()
    doc = await db.chat_sessions.find_one({"chat_id": chat_id})
    if not doc:
        return []
    return doc.get("messages", [])[-(CHAT_HISTORY_LIMIT * 2):]

async def append_turn(chat_id: int, role: str, content: str) -> None:
    db = await _get_db()
    now = datetime.now(timezone.utc)
    await db.chat_sessions.update_one(
        {"chat_id": chat_id},
        {"$push": {"messages": {
            "role": role, "content": content, "ts": now
        }},
         "$setOnInsert": {"created_at": now}},
        upsert=True
    )
    # Trim server-side (keep latest ~2*limit to include both user+assistant)
    await db.chat_sessions.update_one(
        {"chat_id": chat_id},
        {"$push": {
            "messages": {
                "$each": [],
                "$slice": -(CHAT_HISTORY_LIMIT * 2)
            }
        }}
    )

# -------------------- LLM --------------------
def _make_llm() -> Llama:
    # llama.cpp auto-detects chat template from GGUF metadata for most instruct models.
    # If your model needs a specific template, pass chat_format="qwen2" (etc.).
    return Llama(
        model_path=LLM_MODEL_PATH,
        n_ctx=LLM_CTX,
        n_threads=LLM_THREADS if LLM_THREADS > 0 else None,  # None => auto
        verbose=False,
    )

async def _ensure_llm() -> Llama:
    global _llm
    if _llm is not None:
        return _llm
    async with _llm_lock:
        if _llm is None:
            # create in a thread to avoid blocking the event loop
            _llm = await asyncio.to_thread(_make_llm)
    return _llm

def _build_messages(history: List[Dict[str, str]], user_text: str) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        role = turn.get("role")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": user_text})
    return msgs

async def _llm_reply(user_text: str, history: List[Dict[str, str]]) -> str:
    llm = await _ensure_llm()
    messages = _build_messages(history, user_text)

    def _call():
        # llama-cpp-python chat completion
        out = llm.create_chat_completion(
            messages=messages,
            temperature=LLM_TEMP,
            max_tokens=LLM_MAX_TOKENS,
        )
        return out["choices"][0]["message"]["content"].strip()

    # run on worker thread (llm is CPU-bound)
    return await asyncio.to_thread(_call)

# -------------------- PUBLIC HANDLER --------------------
async def chatbot_reply_llm(client: Client, message: Message):
    """
    Lightweight LLM chatbot that replies ONLY when the user replies to the bot's message.
    Register in main.py with:
        from pyrogram.handlers import MessageHandler
        from pyrogram import filters
        app.add_handler(MessageHandler(chatbot_reply_llm, filters.reply & filters.text))
    """
    if not message.reply_to_message:
        return
    src = message.reply_to_message
    if not src.from_user or not src.from_user.is_self:
        return  # only when replying to bot

    text = message.text or message.caption
    if not text:
        return

    chat_id = message.chat.id

    try:
        history = await load_history(chat_id)
        # Append current user turn before inference (so streaming/interruptions still preserve context)
        await append_turn(chat_id, "user", text)

        reply = await _llm_reply(text, history)
        reply = reply if len(reply) <= 3900 else reply[:3895] + "…"

        await append_turn(chat_id, "assistant", reply)
        await message.reply_text(reply)
    except Exception as e:
        await message.reply_text("LLM is warming up or busy. Try again in a moment.")
        print("Error:", e)
