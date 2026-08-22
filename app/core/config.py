from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    """
    Application configuration.
    Values are loaded from environment variables.
    """

    # Application
    ENVIRONMENT: str = "development"

    LOG_LEVEL: str = "INFO"

    RUNNING_IN_DOCKER: bool = False


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

    HTTP_TIMEOUT_SECONDS: float = 12
    HTTP_USER_AGENT: str = "LobBot/2.0"
    TMDB_BEARER_TOKEN: str | None = None
    LIBRETRANSLATE_URL: str = "https://libretranslate.com"
    LIBRETRANSLATE_API_KEY: str | None = None
    TRANSLATION_DEFAULT_LANGUAGE: str = "en"

    @property
    def runtime_mongo_uri(self) -> str:
        return self._localize_compose_host(self.MONGO_URI, "mongodb")

    @property
    def runtime_libretranslate_url(self) -> str:
        return self._localize_compose_host(
            self.LIBRETRANSLATE_URL,
            "libretranslate",
        )

    def _localize_compose_host(self, value: str, compose_host: str) -> str:
        """Map a private Compose hostname to loopback for host development."""
        if self.RUNNING_IN_DOCKER:
            return value
        parsed = urlsplit(value)
        if parsed.hostname != compose_host:
            return value
        userinfo = parsed.netloc.rsplit("@", 1)[0] + "@" if "@" in parsed.netloc else ""
        port = f":{parsed.port}" if parsed.port else ""
        return urlunsplit(parsed._replace(netloc=f"{userinfo}127.0.0.1{port}"))


@lru_cache
def get_settings():

    return Settings()


settings = get_settings()
