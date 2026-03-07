import os
from dotenv import load_dotenv

load_dotenv()

# Load in required API configuration items to start bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
MONGO_URL = os.getenv("MONGO_URL")

# Raise an error if the required items are not set already
if not API_ID or not API_HASH or not BOT_TOKEN or not SESSION_STRING:
    raise ValueError("API_ID, API_HASH, BOT_TOKEN, and SESSION_STRING must be set in the .env file")

if not MONGO_URL:
    raise ValueError("MONGO_URI must be defined inside .env file!")