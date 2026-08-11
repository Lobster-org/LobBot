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

        self.client = AsyncIOMotorClient(
            settings.MONGO_URI
        )

        self.database = self.client[
            settings.MONGO_DATABASE
        ]

        # Verify the connection.
        await self.client.admin.command("ping")

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

        logger.info("MongoDB indexes initialized")


mongodb = MongoDB()
