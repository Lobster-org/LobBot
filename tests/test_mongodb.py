import pytest

from app.database.mongodb import mongodb


@pytest.mark.asyncio
async def test_mongodb_connection():

    await mongodb.connect()

    database = mongodb.get_database()

    assert database is not None

    await mongodb.disconnect()