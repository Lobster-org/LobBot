from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from app.database.collections import GROUPS, MODERATION_ACTIONS
from app.database.repositories.base import BaseRepository
from app.modules.moderation.config import (
    EXPIRATION_CLAIM_TIMEOUT_SECONDS,
)
from app.modules.moderation.models.punishment import (
    Punishment,
    PunishmentStatus,
    PunishmentType,
)


class ModerationRepository(BaseRepository):
    def __init__(self, database):
        super().__init__(database, MODERATION_ACTIONS)

    async def create(self, punishment: Punishment) -> Punishment:
        result = await self.insert_one(punishment.to_document())
        punishment.id = result.inserted_id
        return punishment

    async def get_warnings(
        self,
        chat_id: int,
        user_id: int,
        limit: int = 100,
    ) -> list[Punishment]:
        cursor = self.collection.find(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "action": PunishmentType.WARN.value,
                "status": PunishmentStatus.ACTIVE.value,
            }
        ).sort("created_at", 1)
        documents = await cursor.to_list(length=limit)
        return [Punishment.from_document(item) for item in documents]

    async def count_warnings(self, chat_id: int, user_id: int) -> int:
        return await self.collection.count_documents(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "action": PunishmentType.WARN.value,
                "status": PunishmentStatus.ACTIVE.value,
            }
        )

    async def remove_warning(
        self,
        chat_id: int,
        warning_id: str,
        removed_by: int,
    ) -> Punishment | None:
        try:
            object_id = ObjectId(warning_id)
        except Exception:
            return None

        document = await self.collection.find_one_and_update(
            {
                "_id": object_id,
                "chat_id": chat_id,
                "action": PunishmentType.WARN.value,
                "status": PunishmentStatus.ACTIVE.value,
            },
            {
                "$set": {
                    "status": PunishmentStatus.REMOVED.value,
                    "removed_by": removed_by,
                    "removed_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return Punishment.from_document(document) if document else None

    async def resolve_warnings(
        self,
        chat_id: int,
        user_id: int,
        resolved_by: int,
    ) -> int:
        result = await self.collection.update_many(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "action": PunishmentType.WARN.value,
                "status": PunishmentStatus.ACTIVE.value,
            },
            {
                "$set": {
                    "status": PunishmentStatus.EXPIRED.value,
                    "resolved_by": resolved_by,
                    "resolved_at": datetime.now(timezone.utc),
                    "resolution": "automod_escalation",
                }
            },
        )
        return result.modified_count

    async def remove_active_action(
        self,
        chat_id: int,
        user_id: int,
        action: PunishmentType,
        removed_by: int,
    ) -> Punishment | None:
        document = await self.collection.find_one_and_update(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "action": action.value,
                "status": PunishmentStatus.ACTIVE.value,
            },
            {
                "$set": {
                    "status": PunishmentStatus.REMOVED.value,
                    "removed_by": removed_by,
                    "removed_at": datetime.now(timezone.utc),
                }
            },
            sort=[("created_at", -1)],
            return_document=ReturnDocument.AFTER,
        )
        return Punishment.from_document(document) if document else None

    async def claim_expired_mutes(
        self,
        now: datetime,
        limit: int,
    ) -> list[Punishment]:
        stale_before = now - timedelta(
            seconds=EXPIRATION_CLAIM_TIMEOUT_SECONDS
        )
        claimable = {
            "$or": [
                {"status": PunishmentStatus.ACTIVE.value},
                {
                    "status": PunishmentStatus.PROCESSING.value,
                    "processing_at": {"$lte": stale_before},
                },
            ]
        }
        cursor = self.collection.find(
            {
                "action": PunishmentType.MUTE.value,
                "expires_at": {"$lte": now},
                **claimable,
            }
        ).sort("expires_at", 1).limit(limit)
        candidates = await cursor.to_list(length=limit)
        claimed = []

        for candidate in candidates:
            document = await self.collection.find_one_and_update(
                {
                    "_id": candidate["_id"],
                    **claimable,
                },
                {
                    "$set": {
                        "status": PunishmentStatus.PROCESSING.value,
                        "processing_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            if document:
                claimed.append(Punishment.from_document(document))

        return claimed

    async def complete_expiration(self, action_id) -> None:
        await self.update_one(
            {"_id": action_id},
            {
                "$set": {
                    "status": PunishmentStatus.EXPIRED.value,
                    "expired_at": datetime.now(timezone.utc),
                },
                "$unset": {"processing_at": ""},
            },
        )

    async def release_expiration(self, action_id, error: str) -> None:
        await self.update_one(
            {"_id": action_id},
            {
                "$set": {
                    "status": PunishmentStatus.ACTIVE.value,
                    "last_error": error[:500],
                },
                "$unset": {"processing_at": ""},
            },
        )


class AutomodRepository(BaseRepository):
    SETTINGS_PATH = "settings.moderation.automod"

    def __init__(self, database):
        super().__init__(database, GROUPS)

    async def get_config(self, chat_id: int) -> dict:
        group = await self.find_one({"telegram_id": chat_id})
        if not group:
            return {}
        return (
            group.get("settings", {})
            .get("moderation", {})
            .get("automod", {})
        )

    async def set_config(self, chat_id: int, config: dict) -> None:
        await self.update_one(
            {"telegram_id": chat_id},
            {"$set": {self.SETTINGS_PATH: config}},
        )
