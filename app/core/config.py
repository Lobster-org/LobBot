from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    """
    Application configuration.
    Values are loaded from environment variables.
    """

    # Application
    ENVIRONMENT: str = "development"

    LOG_LEVEL: str = "INFO"


    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # Telegram MTProto Voice Client
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    VOICE_SESSION_NAME: str = "lobbot_voice"


    # MongoDB
    MONGO_URI: str

    MONGO_DATABASE: str = "lobbot"


    # Redis
    REDIS_URI: str


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # class Telegram:
    #     token: str
    
    # class Database:
    #     mongo_uri: str
    
    # class Redis:
    #     uri: str
    
    MUSIC_STORAGE_PATH: str = "storage/music"


@lru_cache
def get_settings():

    return Settings()


settings = get_settings()