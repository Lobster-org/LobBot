from pyrogram import Client, filters
from config import BOT_TOKEN, API_ID, API_HASH, SESSION_STRING

# Handlers
from handlers import urban
from games import rps

app = Client("LobBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@app.on_message(filters.private & filters.command("start"))
def private_chat_handler(client, message):
    message.reply_text("Hello! I'm LobBot. Ready to assist to the best I can.")
    
@app.on_message(filters.command("start") & filters.group)
def group_start_handle(client, message):
    message.reply_text("Hello! I'm LobBot. What's boomin' in this group?")
        
if __name__ == "__main__":
    urban.add_handlers(app)
    rps.add_handlers(app)
    app.run()