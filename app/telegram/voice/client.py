from telethon import TelegramClient
from pytgcalls import PyTgCalls

from app.core.config import settings


def create_voice_client():

    client = TelegramClient(
        settings.VOICE_SESSION_NAME,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH,
    )

    calls = PyTgCalls(
        client
    )

    return client, calls