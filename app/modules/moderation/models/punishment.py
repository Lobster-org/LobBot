from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class PunishmentType(str, Enum):
    WARN = "warn"
    MUTE = "mute"
    UNMUTE = "unmute"
    BAN = "ban"
    PURGE = "purge"


class PunishmentStatus(str, Enum):
    ACTIVE = "active"
    PROCESSING = "processing"
    REMOVED = "removed"
    EXPIRED = "expired"


@dataclass(slots=True)
class Punishment:
    chat_id: int
    moderator_id: int
    action: PunishmentType
    reason: str
    created_at: datetime
    user_id: int | None = None
    expires_at: datetime | None = None
    status: PunishmentStatus = PunishmentStatus.ACTIVE
    id: Any = None

    def to_document(self) -> dict:
        return {
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "moderator_id": self.moderator_id,
            "action": self.action.value,
            "reason": self.reason,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "created_at": self.created_at,
        }

    @classmethod
    def from_document(cls, document: dict):
        return cls(
            id=document.get("_id"),
            chat_id=int(document["chat_id"]),
            user_id=(
                int(document["user_id"])
                if document.get("user_id") is not None
                else None
            ),
            moderator_id=int(document["moderator_id"]),
            action=PunishmentType(document["action"]),
            reason=document.get("reason") or "",
            expires_at=document.get("expires_at"),
            status=PunishmentStatus(
                document.get("status", PunishmentStatus.ACTIVE.value)
            ),
            created_at=document["created_at"],
        )
