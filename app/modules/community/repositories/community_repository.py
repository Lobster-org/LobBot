from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.database.collections import (
    COMMUNITY_SETTINGS,
    COMMUNITY_VERIFICATIONS,
)
from app.database.repositories.base import BaseRepository
from app.modules.community.config import (
    VERIFICATION_CLAIM_TIMEOUT_SECONDS,
)
from app.modules.community.models.settings import CommunitySettings


class CommunityRepository(BaseRepository):
    def __init__(self, database):
        super().__init__(database, COMMUNITY_SETTINGS)

    async def get_settings(self, chat_id: int) -> CommunitySettings:
        return CommunitySettings.from_document(
            chat_id,
            await self.find_one({"chat_id": chat_id}),
        )

    async def save_settings(self, settings: CommunitySettings) -> None:
        now = datetime.now(timezone.utc)
        document = settings.to_document()
        document.pop("chat_id", None)
        document["updated_at"] = now
        await self.update_one(
            {"chat_id": settings.chat_id},
            {
                "$set": document,
                "$setOnInsert": {
                    "chat_id": settings.chat_id,
                    "created_at": now,
                },
            },
            upsert=True,
        )


class VerificationRepository(BaseRepository):
    def __init__(self, database):
        super().__init__(database, COMMUNITY_VERIFICATIONS)

    async def create_pending(
        self,
        chat_id: int,
        user_id: int,
        expires_at: datetime,
    ) -> tuple[dict, bool]:
        existing = await self.find_one(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "status": "pending",
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            }
        )
        if existing:
            return existing, False

        now = datetime.now(timezone.utc)
        await self.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {
                "$set": {
                    "status": "pending",
                    "created_at": now,
                    "expires_at": expires_at,
                },
                "$unset": {
                    "verified_at": "",
                    "expired_at": "",
                    "removed_at": "",
                    "processing_at": "",
                    "verifying_at": "",
                    "last_error": "",
                },
            },
            upsert=True,
        )
        document = await self.find_one(
            {"chat_id": chat_id, "user_id": user_id}
        )
        return document, True

    async def claim_verification(self, chat_id: int, user_id: int):
        now = datetime.now(timezone.utc)
        return await self.collection.find_one_and_update(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "status": "pending",
                "expires_at": {"$gt": now},
            },
            {"$set": {"status": "verifying", "verifying_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    async def mark_verified(self, chat_id: int, user_id: int) -> bool:
        result = await self.update_one(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "status": "verifying",
            },
            {
                "$set": {
                    "status": "verified",
                    "verified_at": datetime.now(timezone.utc),
                },
                "$unset": {"verifying_at": ""},
            },
        )
        return result.modified_count > 0

    async def release_verification(self, chat_id: int, user_id: int):
        await self.update_one(
            {"chat_id": chat_id, "user_id": user_id, "status": "verifying"},
            {"$set": {"status": "pending"}, "$unset": {"verifying_at": ""}},
        )

    async def mark_removed(self, chat_id: int, user_id: int) -> bool:
        result = await self.update_one(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "status": {"$in": ["pending", "processing", "verifying"]},
            },
            {
                "$set": {
                    "status": "removed",
                    "removed_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0

    async def claim_expired(self, now: datetime, limit: int) -> list[dict]:
        stale_before = now - timedelta(
            seconds=VERIFICATION_CLAIM_TIMEOUT_SECONDS
        )
        claimable = {
            "$or": [
                {"status": "pending"},
                {
                    "status": "processing",
                    "processing_at": {"$lte": stale_before},
                },
                {
                    "status": "verifying",
                    "verifying_at": {"$lte": stale_before},
                },
            ]
        }
        cursor = (
            self.collection.find(
                {"expires_at": {"$lte": now}, **claimable}
            )
            .sort("expires_at", 1)
            .limit(limit)
        )
        candidates = await cursor.to_list(length=limit)
        claimed = []
        for candidate in candidates:
            document = await self.collection.find_one_and_update(
                {"_id": candidate["_id"], **claimable},
                {
                    "$set": {
                        "status": "processing",
                        "processing_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            if document:
                claimed.append(document)
        return claimed

    async def mark_expired(self, record_id) -> None:
        await self.update_one(
            {"_id": record_id, "status": "processing"},
            {
                "$set": {
                    "status": "expired",
                    "expired_at": datetime.now(timezone.utc),
                },
                "$unset": {"processing_at": ""},
            },
        )

    async def release_claim(self, record_id, error: str) -> None:
        await self.update_one(
            {"_id": record_id, "status": "processing"},
            {
                "$set": {
                    "status": "pending",
                    "last_error": error[:500],
                },
                "$unset": {"processing_at": ""},
            },
        )
