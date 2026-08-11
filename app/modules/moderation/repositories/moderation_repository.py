from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.database.collections import MODERATION_ACTIONS
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
