from types import SimpleNamespace

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from telethon.errors import InviteHashExpiredError

from app.telegram.voice.membership import VoiceAccountMembershipService
from app.modules.music.handler import play_command
from app.modules.music.state import music_state


class Bot:
    def __init__(self, statuses, invite_links=None):
        self.statuses = iter(statuses)
        self.invite_links = iter(invite_links or ["https://t.me/+secret_hash"])
        self.created = []
        self.revoked = []
        self.promoted = []

    async def get_chat_member(self, chat_id, user_id):
        status = next(self.statuses)
        if isinstance(status, Exception):
            raise status
        if isinstance(status, tuple):
            status, can_manage_video_chats = status
        else:
            can_manage_video_chats = False
        return SimpleNamespace(
            status=status,
            can_manage_video_chats=can_manage_video_chats,
        )

    async def create_chat_invite_link(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(invite_link=next(self.invite_links))

    async def revoke_chat_invite_link(self, **kwargs):
        self.revoked.append(kwargs)

    async def promote_chat_member(self, **kwargs):
        self.promoted.append(kwargs)


class Client:
    def __init__(self, fail=False, failures=None):
        self.requests = []
        self.fail = fail
        self.failures = iter(failures or [])

    async def __call__(self, request):
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("join failed")
        failure = next(self.failures, None)
        if failure:
            raise failure


def service(bot, client=None):
    return VoiceAccountMembershipService(
        bot,
        client or Client(),
        SimpleNamespace(id=55, username="LobMusic"),
    )


@pytest.mark.asyncio
async def test_voice_membership_recognizes_present_and_absent_account():
    present = service(Bot([ChatMemberStatus.MEMBER]))
    assert await present.is_member(-100) is True

    error = TelegramBadRequest(method=SimpleNamespace(), message="user not found")
    absent = service(Bot([error]))
    assert await absent.is_member(-100) is False


@pytest.mark.asyncio
async def test_voice_account_requires_manage_video_chats_permission():
    regular = service(Bot([ChatMemberStatus.MEMBER]))
    assert (await regular.get_readiness(-100)).ready is False

    admin_without_permission = service(Bot([
        (ChatMemberStatus.ADMINISTRATOR, False),
    ]))
    assert (await admin_without_permission.get_readiness(-100)).ready is False

    admin = service(Bot([(ChatMemberStatus.ADMINISTRATOR, True)]))
    assert (await admin.get_readiness(-100)).ready is True

    creator = service(Bot([ChatMemberStatus.CREATOR]))
    assert (await creator.get_readiness(-100)).ready is True


@pytest.mark.asyncio
async def test_voice_account_can_be_promoted_for_voice_chat_management():
    bot = Bot([
        ChatMemberStatus.MEMBER,
        (ChatMemberStatus.ADMINISTRATOR, True),
    ])
    membership = service(bot)

    assert await membership.promote(-100) is True
    assert bot.promoted == [{
        "chat_id": -100,
        "user_id": 55,
        "can_manage_video_chats": True,
    }]


@pytest.mark.asyncio
async def test_voice_account_joins_with_one_use_invite_and_revokes_it():
    bot = Bot([ChatMemberStatus.LEFT, ChatMemberStatus.MEMBER])
    client = Client()
    membership = service(bot, client)

    assert await membership.join(-100) is True
    assert bot.created[0]["member_limit"] == 1
    assert client.requests[0].hash == "secret_hash"
    assert bot.revoked[0]["invite_link"] == "https://t.me/+secret_hash"


@pytest.mark.asyncio
async def test_failed_voice_join_still_revokes_invite_link():
    bot = Bot([ChatMemberStatus.LEFT])
    membership = service(bot, Client(fail=True))

    with pytest.raises(RuntimeError, match="join failed"):
        await membership.join(-100)

    assert len(bot.revoked) == 1


@pytest.mark.asyncio
async def test_expired_fresh_invite_is_recreated_and_retried_once():
    bot = Bot(
        [ChatMemberStatus.LEFT, ChatMemberStatus.MEMBER],
        invite_links=["https://t.me/+expired", "https://t.me/+fresh"],
    )
    client = Client(failures=[InviteHashExpiredError(SimpleNamespace())])
    membership = service(bot, client)

    assert await membership.join(-100) is True
    assert [request.hash for request in client.requests] == ["expired", "fresh"]
    assert len(bot.created) == 2
    assert len(bot.revoked) == 2


def test_invite_hash_supports_legacy_telegram_links():
    assert VoiceAccountMembershipService._invite_hash(
        "https://t.me/joinchat/legacy_hash"
    ) == "legacy_hash"


@pytest.mark.asyncio
async def test_play_stops_before_search_when_voice_account_is_absent():
    class Membership:
        username = "LobMusic"
        display_name = "@LobMusic"
        async def get_readiness(self, chat_id):
            return SimpleNamespace(is_member=False, can_manage_voice_chats=False)

    replies = []
    async def reply(text, **kwargs):
        replies.append((text, kwargs))
        return SimpleNamespace()

    previous = music_state.voice_membership
    music_state.voice_membership = Membership()
    try:
        await play_command(SimpleNamespace(
            text="/play Blinding Lights",
            chat=SimpleNamespace(id=-100, type="supergroup"),
            from_user=SimpleNamespace(id=1),
            reply=reply,
        ))
    finally:
        music_state.voice_membership = previous

    assert "is not in this group" in replies[0][0]
    keyboard = replies[0][1]["reply_markup"]
    assert keyboard.inline_keyboard[0][0].callback_data == "music:invite_voice"
