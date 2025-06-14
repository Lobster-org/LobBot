from pyrogram import Client
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH:
    raise ValueError("API_ID and API_HASH must be set in the .env file")

with Client("gen_session", api_id=API_ID, api_hash=API_HASH) as app:
    print("\nYour session string:\n")
    print(app.export_session_string())