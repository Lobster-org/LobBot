from datetime import datetime, timezone
from typing import Any


def create_group_document(
    telegram_id: int,
    title: str | None,
    group_type: str,
) -> dict[str, Any]:
    """
    Create the initial MongoDB document
    for a Telegram group.
    """

    now = datetime.now(timezone.utc)

    return {
        "telegram_id": telegram_id,
        "title": title,
        "type": group_type,
        "created_at": now,
        "last_seen": now,
        "bot_status": "active",
        "settings": {},
        "enabled_modules": [],
        "roles": {},
        "permission_overrides": {},
    }
