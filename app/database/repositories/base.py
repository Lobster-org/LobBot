from typing import Any


class BaseRepository:

    def __init__(self, database, collection_name: str):

        self.database = database

        self.collection = database[
            collection_name
        ]

    async def find_one(
        self,
        query: dict[str, Any]
    ):

        return await self.collection.find_one(
            query
        )

    async def insert_one(
        self,
        document: dict[str, Any]
    ):

        return await self.collection.insert_one(
            document
        )

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False
    ):

        return await self.collection.update_one(
            query,
            update,
            upsert=upsert
        )

    async def delete_one(
        self,
        query: dict[str, Any]
    ):

        return await self.collection.delete_one(
            query
        )
    
    async def find_many(
        self,
        query: dict[str, Any],
        limit: int = 100,
    ):
        cursor = self.collection.find(query)

        return await cursor.to_list(
            length=limit
        )