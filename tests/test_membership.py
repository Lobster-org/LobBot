from types import SimpleNamespace

import pytest

from app.telegram.membership import TelegramMembershipProvider


@pytest.mark.asyncio
async def test_membership_provider_resolves_public_username_with_user_client():
    class Client:
        async def get_entity(self, username):
            assert username == "newmember"
            return SimpleNamespace(id=4321)

    provider = TelegramMembershipProvider(SimpleNamespace(), Client())

    assert await provider.resolve_user_id("@newmember") == 4321


@pytest.mark.asyncio
async def test_membership_provider_handles_unknown_username():
    class Client:
        async def get_entity(self, username):
            raise ValueError("not found")

    provider = TelegramMembershipProvider(SimpleNamespace(), Client())

    assert await provider.resolve_user_id("@missing") is None
