from urllib.parse import urlsplit

from app.core.config import Settings, settings


def test_config_loaded():

    assert settings.ENVIRONMENT is not None

    assert settings.MONGO_URI is not None


def test_host_runtime_maps_compose_service_names_to_loopback():
    config = Settings(
        TELEGRAM_BOT_TOKEN="token",
        TELEGRAM_API_ID=1,
        TELEGRAM_API_HASH="hash",
        MONGO_URI="mongodb://user:password@mongodb:27017/lobbot?authSource=admin",
        REDIS_URI="redis://unused",
        LIBRETRANSLATE_URL="http://libretranslate:5000",
        RUNNING_IN_DOCKER=False,
    )
    assert urlsplit(config.runtime_mongo_uri).hostname == "127.0.0.1"
    assert urlsplit(config.runtime_libretranslate_url).hostname == "127.0.0.1"
    assert "authSource=admin" in config.runtime_mongo_uri


def test_docker_runtime_preserves_compose_service_names():
    config = Settings(
        TELEGRAM_BOT_TOKEN="token",
        TELEGRAM_API_ID=1,
        TELEGRAM_API_HASH="hash",
        MONGO_URI="mongodb://mongodb:27017/lobbot",
        REDIS_URI="redis://unused",
        LIBRETRANSLATE_URL="http://libretranslate:5000",
        RUNNING_IN_DOCKER=True,
    )
    assert urlsplit(config.runtime_mongo_uri).hostname == "mongodb"
    assert urlsplit(config.runtime_libretranslate_url).hostname == "libretranslate"
