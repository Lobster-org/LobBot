import logging

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


logger = logging.getLogger(__name__)


class MongoDB:

    def __init__(self):
        self.client: AsyncIOMotorClient | None = None
        self.database = None

    async def connect(self):
        """
        Establish a connection to MongoDB.
        """

        if self.client is not None:
            return

        client = AsyncIOMotorClient(settings.MONGO_URI)

        try:
            await client.admin.command("ping")
        except Exception:
            client.close()
            raise

        self.client = client
        self.database = client[settings.MONGO_DATABASE]

        logger.info(
            "MongoDB connected: database=%s",
            settings.MONGO_DATABASE,
        )

    async def disconnect(self):
        """
        Close the MongoDB connection.
        """

        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            logger.info("MongoDB disconnected")

    def get_database(self):
        """
        Return the active database instance.
        """

        if self.database is None:
            raise RuntimeError(
                "MongoDB has not been connected."
            )

        return self.database

    async def initialize_indexes(self):
        """
        Create MongoDB indexes required by the application.
        """

        database = self.get_database()

        await database["users"].create_index(
            "telegram_id",
            unique=True,
        )

        await database["groups"].create_index(
            "telegram_id",
            unique=True,
        )

        await database["music_cache"].create_index(
            [
                ("source", 1),
                ("source_id", 1),
            ],
            unique=True,
        )

        await database["music_cache"].create_index(
            "last_used"
        )

        await database["music_sessions"].create_index(
            "chat_id",
            unique=True,
        )

        await database["music_sessions"].create_index(
            "updated_at"
        )

        await database["moderation_actions"].create_index(
            [
                ("chat_id", 1),
                ("user_id", 1),
            ]
        )

        await database["community_settings"].create_index(
            "chat_id",
            unique=True,
        )

        await database["community_verifications"].create_index(
            [
                ("chat_id", 1),
                ("user_id", 1),
            ],
            unique=True,
        )

        await database["economy_profiles"].create_index(
            [("chat_id", 1), ("user_id", 1)], unique=True,
        )
        for field in ("xp", "coins", "games_won"):
            await database["economy_profiles"].create_index(
                [("chat_id", 1), (field, -1)],
            )
        await database["economy_transactions"].create_index(
            [("chat_id", 1), ("user_id", 1), ("created_at", -1)],
        )
        await database["economy_settings"].create_index(
            "chat_id", unique=True,
        )
        await database["economy_bets"].create_index(
            [("match_id", 1), ("user_id", 1)], unique=True,
        )
        await database["economy_bets"].create_index(
            [("status", 1), ("created_at", 1)],
        )

        await database["community_verifications"].create_index(
            [
                ("status", 1),
                ("expires_at", 1),
            ]
        )

        await database["moderation_actions"].create_index(
            [
                ("chat_id", 1),
                ("created_at", -1),
            ]
        )

        await database["moderation_actions"].create_index(
            [
                ("action", 1),
                ("status", 1),
                ("expires_at", 1),
            ]
        )

        logger.info("MongoDB indexes initialized")


mongodb = MongoDB()
