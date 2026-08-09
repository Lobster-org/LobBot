import asyncio
from app.core.config import settings
from app.database.mongodb import mongodb
from app.telegram.client import bot, dispatcher
from app.core.modules import module_loader

async def main():

    print(
        f"""
        Starting LobBot

        Environment:
        {settings.ENVIRONMENT}

        Database:
        {settings.MONGO_DATABASE}
        """
    )
    
    try:

        await mongodb.connect()
        
        await mongodb.initialize_indexes()

        print("LobBot initialization complete.")
        
        await module_loader.setup(
            dispatcher
        )
        
        await dispatcher.start_polling(
            bot
        )        

    except Exception as error:

        print(
            f"Failed to start application: {error}"
        )
        raise

    finally:

        await module_loader.shutdown()
        await bot.session.close()
        await mongodb.disconnect()
        



if __name__ == "__main__":
    asyncio.run(main())