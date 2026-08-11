from types import SimpleNamespace

import pytest

from app.core.events import EventBus
from app.modules.community.events import MEMBER_JOINED
from app.modules.community.handlers import member_joined, verify_member
from app.modules.community.models.settings import CommunitySettings
from app.modules.community.services.community_service import CommunityService
from app.modules.community.services.verification_service import VerificationService
from app.modules.community.templates import TemplateRenderer, WELCOME_VARIATION_COUNT, GOODBYE_VARIATION_COUNT


class Randomizer:
    def choice(self, values): return values[0]


class Repository:
    def __init__(self, settings=None): self.value = settings or CommunitySettings(-100)
    async def get_settings(self, chat_id): return self.value
    async def save_settings(self, settings): self.value = settings


class Verification:
    def __init__(self): self.begun = []
    async def begin(self, chat_id, user, timeout): self.begun.append((chat_id, user.id, timeout)); return True
    async def member_left(self, chat_id, user_id): pass
    async def verify(self, chat_id, user_id): return True


class Bot:
    async def get_chat_member_count(self, chat_id): return 42
    async def get_me(self): return SimpleNamespace(id=999)


class Message:
    def __init__(self):
        self.chat = SimpleNamespace(id=-100, title="Fun <Group>")
        self.answers = []
        self.deleted = False
    async def answer(self, text, **kwargs): self.answers.append((text, kwargs))
    async def delete(self): self.deleted = True


def user(user_id=10, bot=False):
    return SimpleNamespace(id=user_id, full_name="A <User>", first_name="A", username=None, is_bot=bot)


def test_default_settings_and_fun_message_counts():
    settings = CommunitySettings(-100)
    assert settings.welcome_enabled is True
    assert settings.goodbye_enabled is False
    assert settings.verification_enabled is False
    assert WELCOME_VARIATION_COUNT == 80
    assert GOODBYE_VARIATION_COUNT == 64


def test_template_rendering_is_safe_and_validated():
    renderer = TemplateRenderer(Randomizer())
    text = renderer.render("Hi {mention} in {group}", {"mention": '<a href="tg://user?id=1">A</a>', "group": "G", **{k: "x" for k in ("name", "first_name", "username", "member_count")}})
    assert "tg://user" in text
    with pytest.raises(ValueError): renderer.validate("Hello {unknown}")


@pytest.mark.asyncio
async def test_join_sends_welcome_and_event():
    bus = EventBus(); events = []
    async def listener(event): events.append(event)
    bus.subscribe(MEMBER_JOINED, listener)
    service = CommunityService(Repository(), Verification(), Bot(), bus)
    service.renderer.randomizer = Randomizer()
    message = Message()
    await service.handle_join(message, user())
    assert "A &lt;User&gt;" in message.answers[0][0]
    assert events[0].payload["user_id"] == 10


@pytest.mark.asyncio
async def test_join_handler_ignores_bots():
    calls = []
    class Service:
        async def handle_join(self, message, member): calls.append(member.id)
    message = SimpleNamespace(new_chat_members=[user(10), user(20, True)])
    await member_joined(message, Service())
    assert calls == [10]


@pytest.mark.asyncio
async def test_wrong_user_cannot_verify():
    answers = []
    callback = SimpleNamespace(data="community:verify:10", from_user=SimpleNamespace(id=11), answer=lambda *args, **kwargs: None)
    async def answer(*args, **kwargs): answers.append((args, kwargs))
    callback.answer = answer
    await verify_member(callback, SimpleNamespace())
    assert answers[0][1]["show_alert"] is True
    assert "not for you" in answers[0][0][0]


@pytest.mark.asyncio
async def test_verification_claim_restores_permissions_and_emits_event():
    class Repo:
        async def claim_verification(self, chat_id, user_id): return {"status": "verifying"}
        async def mark_verified(self, chat_id, user_id): return True
        async def release_verification(self, chat_id, user_id): raise AssertionError
    class VerifyBot:
        def __init__(self): self.restricted = []
        async def get_chat(self, chat_id): return SimpleNamespace(permissions=None)
        async def restrict_chat_member(self, **kwargs): self.restricted.append(kwargs)
    bus = EventBus(); events = []
    async def record(event): events.append(event)
    bus.subscribe("community.member_verified", record)
    bot = VerifyBot()
    service = VerificationService(Repo(), bot, bus)
    assert await service.verify(-100, 10) is True
    assert bot.restricted[0]["user_id"] == 10
    assert events[0].payload == {"chat_id": -100, "user_id": 10}


@pytest.mark.asyncio
async def test_expired_verification_is_kicked_and_recorded():
    class Repo:
        async def claim_expired(self, now, limit): return [{"_id": "v1", "chat_id": -100, "user_id": 10}]
        async def mark_expired(self, record_id): self.expired = record_id
        async def release_claim(self, *args): raise AssertionError
    class VerifyBot:
        def __init__(self): self.calls = []
        async def ban_chat_member(self, **kwargs): self.calls.append("ban")
        async def unban_chat_member(self, **kwargs): self.calls.append("unban")
    repo = Repo(); bot = VerifyBot()
    service = VerificationService(repo, bot, EventBus())
    assert await service.process_expired() == 1
    assert bot.calls == ["ban", "unban"]
    assert repo.expired == "v1"


@pytest.mark.asyncio
async def test_verification_worker_stops_cleanly():
    class Repo:
        async def claim_expired(self, now, limit): return []
    service = VerificationService(Repo(), Bot(), EventBus(), poll_seconds=60)
    await service.start()
    task = service._task
    await service.stop()
    assert task.done()
    assert service._task is None
