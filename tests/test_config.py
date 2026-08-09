from app.core.config import settings


def test_config_loaded():

    assert settings.ENVIRONMENT is not None

    assert settings.MONGO_URI is not None