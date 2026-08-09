from aiogram import Bot, Dispatcher

from app.core.config import settings

from app.telegram.middleware import (
    DatabaseMiddleware,
)

from app.telegram.debug import (
    DebugMiddleware
)

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN
)


dispatcher = Dispatcher()


database_middleware = (
    DatabaseMiddleware()
)

# Database middleware
dispatcher.message.middleware(
    database_middleware,
)

dispatcher.my_chat_member.middleware(
    database_middleware
)

# Debug middleware
dispatcher.message.middleware(
    DebugMiddleware()
)

dispatcher.my_chat_member.middleware(
    DebugMiddleware()
)
