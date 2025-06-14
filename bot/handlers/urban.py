import requests
from pyrogram import Client, filters
from pyrogram.types import Message

URBAN_API = "https://api.urbandictionary.com/v0/define?term="

def add_handlers(app: Client):
    
    @app.on_message(filters.command("search"))
    async def urban_search(client: Client, message: Message):
        if len(message.command) < 2:
            await message.reply_text("Please provide a word to search. \nUsage: /urban 'word'",)
            return
        
        # Separate word from command
        term = " ".join(message.command[1:])
        
        # Prepare url for searching
        url = URBAN_API + term
        
        try:
            response = requests.get(url).json()
            
            if(response.get("list")):
                definition = response["list"][0]["definition"]
                example = response["list"][0].get("example", "No example available.")
                
                await message.reply_text(f"**Definition:**\n{definition}\n\n**Example:**\n{example}")
            else:
                await message.reply_text("No results found.")

        except Exception as e:
            await message.reply_text(f"Error: {e}")