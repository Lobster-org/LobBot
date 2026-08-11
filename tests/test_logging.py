import logging
from logging.handlers import RotatingFileHandler

from app.core.logging import (
    BACKUP_COUNT,
    MAX_LOG_BYTES,
    RedactingFormatter,
    configure_logging,
    shutdown_logging,
)


def test_logger_initialization_creates_rotating_files(tmp_path):
    try:
        root = configure_logging(
            "DEBUG",
            tmp_path,
        )
        logger = logging.getLogger("tests.logging")
        logger.info("general log entry")
        logger.error("error log entry")

        rotating = [
            handler
            for handler in root.handlers
            if isinstance(handler, RotatingFileHandler)
        ]

        assert len(rotating) == 2
        assert all(
            handler.maxBytes == MAX_LOG_BYTES
            for handler in rotating
        )
        assert all(
            handler.backupCount == BACKUP_COUNT
            for handler in rotating
        )
        assert (tmp_path / "lobbot.log").exists()
        assert (tmp_path / "errors.log").exists()
        assert "general log entry" in (
            tmp_path / "lobbot.log"
        ).read_text()
        assert "error log entry" in (
            tmp_path / "errors.log"
        ).read_text()
    finally:
        shutdown_logging()


def test_configured_log_level_is_applied(tmp_path):
    try:
        root = configure_logging(
            "WARNING",
            tmp_path,
        )

        assert root.level == logging.WARNING
        assert all(
            handler.level in {
                logging.WARNING,
                logging.ERROR,
            }
            for handler in root.handlers
            if getattr(
                handler,
                "_lobbot_managed_handler",
                False,
            )
        )
    finally:
        shutdown_logging()


def test_formatter_redacts_configured_secrets():
    formatter = RedactingFormatter(
        "%(message)s",
        secrets=("super-secret-value",),
    )
    record = logging.LogRecord(
        name="tests.logging",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Failed with super-secret-value",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    assert "super-secret-value" not in formatted
    assert "[REDACTED]" in formatted
