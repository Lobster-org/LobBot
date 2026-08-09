from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from app.core.config import settings


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

        print(
            f"Connected to MongoDB: "
            f"{settings.MONGO_DATABASE}"
        )

    async def disconnect(self):
        """
        Close the MongoDB connection.
        """

        if self.client:
            self.client.close()

            print("MongoDB connection closed.")

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

        print("MongoDB indexes initialized.")


mongodb = MongoDB()