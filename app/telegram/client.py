from aiogram import Bot, Dispatcher

from app.core.config import settings

from app.telegram.middleware import (
    DatabaseMiddleware,
    PermissionMiddleware,
)

from app.telegram.debug import (
    DebugMiddleware
)
from app.telegram.errors import (
    register_error_handlers,
)

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN
)


dispatcher = Dispatcher()

register_error_handlers(dispatcher)


database_middleware = (
    DatabaseMiddleware()
)

permission_middleware = (
    PermissionMiddleware()
)

# Permission filters run before normal middleware,
# so their dependency must be injected in outer scope.
dispatcher.message.outer_middleware(
    permission_middleware,
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
