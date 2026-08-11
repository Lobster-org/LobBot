import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5
_HANDLER_MARKER = "_lobbot_managed_handler"


class RedactingFormatter(logging.Formatter):

    def __init__(self, *args, secrets=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.secrets = tuple(
            str(secret)
            for secret in secrets
            if secret and len(str(secret)) >= 4
        )

    def format(self, record):
        formatted = super().format(record)

        for secret in self.secrets:
            formatted = formatted.replace(
                secret,
                "[REDACTED]",
            )

        return formatted


def resolve_log_level(
    level: str | int,
) -> int:
    if isinstance(level, int):
        return level

    resolved = logging.getLevelName(
        str(level).upper()
    )

    if not isinstance(resolved, int):
        return logging.INFO

    return resolved


def configure_logging(
    log_level: str | int | None = None,
    logs_dir: str | Path = "logs",
) -> logging.Logger:
    level = resolve_log_level(
        log_level or settings.LOG_LEVEL
    )
    directory = Path(logs_dir)
    directory.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root_logger.removeHandler(handler)
            handler.close()

    formatter = RedactingFormatter(
        DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        secrets=(
            settings.TELEGRAM_BOT_TOKEN,
            settings.TELEGRAM_API_HASH,
            settings.MONGO_URI,
        ),
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)

    general_file = RotatingFileHandler(
        directory / "lobbot.log",
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    general_file.setLevel(level)
    general_file.setFormatter(formatter)

    error_file = RotatingFileHandler(
        directory / "errors.log",
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(formatter)

    for handler in (
        console,
        general_file,
        error_file,
    ):
        setattr(handler, _HANDLER_MARKER, True)
        root_logger.addHandler(handler)

    logging.captureWarnings(True)

    return root_logger


def shutdown_logging():
    root_logger = logging.getLogger()

    for handler in list(root_logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root_logger.removeHandler(handler)
            handler.close()
