from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.modules.moderation.models.punishment import (
    Punishment,
    PunishmentStatus,
    PunishmentType,
)
from app.modules.moderation.repositories.moderation_repository import (
    ModerationRepository,
)


class Cursor:
    def __init__(self, documents):
        self.documents = documents
        self.sort_args = None
        self.limit_value = None

    def sort(self, *args):
        self.sort_args = args
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    async def to_list(self, length):
        return self.documents[:length]


class Collection:
    def __init__(self):
        self.documents = []
        self.find_query = None
        self.update_calls = []

    async def insert_one(self, document):
        saved = {**document, "_id": ObjectId()}
        self.documents.append(saved)
        return SimpleNamespace(inserted_id=saved["_id"])

    def find(self, query):
        self.find_query = query
        return Cursor(list(self.documents))

    async def find_one_and_update(self, query, update, **kwargs):
        self.update_calls.append((query, update, kwargs))
        for document in self.documents:
            if document["_id"] == query.get("_id"):
                document.update(update.get("$set", {}))
                return document
        return None

    async def update_one(self, query, update, upsert=False):
        self.update_calls.append((query, update, {"upsert": upsert}))
        return SimpleNamespace(modified_count=1)


class Database:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, name):
        return self.collection


@pytest.mark.asyncio
async def test_repository_atomically_claims_expired_mutes():
    collection = Collection()
    repository = ModerationRepository(Database(collection))
    action = Punishment(
        chat_id=-100,
        user_id=10,
        moderator_id=20,
        action=PunishmentType.MUTE,
        reason="flood",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    await repository.create(action)

    claimed = await repository.claim_expired_mutes(
        datetime.now(timezone.utc),
        100,
    )

    assert claimed[0].status == PunishmentStatus.PROCESSING
    query, update, _ = collection.update_calls[0]
    assert query["_id"] == action.id
    assert "$or" in query
    assert update["$set"]["status"] == "processing"
