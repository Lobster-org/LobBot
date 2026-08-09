import pytest

from app.database.mongodb import mongodb
from app.database.repositories.user import (
    UserRepository,
)
from app.database.repositories.group import (
    GroupRepository,
)


@pytest.fixture
async def database():

    await mongodb.connect()

    database = mongodb.get_database()

    yield database

    await database["users"].delete_many({})
    await database["groups"].delete_many({})

    await mongodb.disconnect()


@pytest.mark.asyncio
async def test_create_user(database):

    repository = UserRepository(
        database
    )

    user = await repository.get_or_create_user(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
    )

    assert user is not None
    assert user["telegram_id"] == 123456789
    assert user["username"] == "testuser"


@pytest.mark.asyncio
async def test_create_group(database):

    repository = GroupRepository(
        database
    )

    group = await repository.get_or_create_group(
        telegram_id=-100123456789,
        title="Test Group",
        group_type="supergroup",
    )

    assert group is not None
    assert group["telegram_id"] == -100123456789
    assert group["title"] == "Test Group"