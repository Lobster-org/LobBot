from datetime import datetime, timezone
from typing import Any


def create_user_document(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None = None,
) -> dict[str, Any]:
    """
    Create the initial MongoDB document for a Telegram user.
    """

    now = datetime.now(timezone.utc)

    return {
        "telegram_id": telegram_id,

        "username": username,

        "first_name": first_name,

        "last_name": last_name,

        "created_at": now,

        "last_seen": now,

        "preferences": {},
    }