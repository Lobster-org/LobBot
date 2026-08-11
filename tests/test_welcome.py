from types import SimpleNamespace

import pytest

from app.core.events import EventBus
from app.modules.welcome.events import MEMBER_JOINED
from app.modules.welcome.handler import welcome_new_members
from app.modules.welcome.messages import INTRODUCTION_COUNT
from app.modules.welcome.service import WelcomeService


class Bot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


class Randomizer:
    def choice(self, values):
        return values[0]


def user(user_id=10, name="New User", is_bot=False):
    return SimpleNamespace(
        id=user_id,
        full_name=name,
        username="newuser",
        is_bot=is_bot,
    )


def test_welcome_has_eighty_possible_introductions():
    assert INTRODUCTION_COUNT == 80


def test_introduction_mentions_user_and_escapes_html():
    service = WelcomeService(
        Bot(),
        EventBus(),
        randomizer=Randomizer(),
    )

    introduction = service.introduction_for(
        user(name="A <B> & Friends")
    )

    assert 'href="tg://user?id=10"' in introduction
    assert "A &lt;B&gt; &amp; Friends" in introduction
    assert "tiny trumpets" in introduction


@pytest.mark.asyncio
async def test_welcome_sends_message_and_emits_member_event():
    bot = Bot()
    bus = EventBus()
    events = []

    async def record(event):
        events.append(event)

    bus.subscribe(MEMBER_JOINED, record)
    service = WelcomeService(bot, bus, randomizer=Randomizer())

    await service.welcome(-100, user())

    assert bot.messages[0]["chat_id"] == -100
    assert bot.messages[0]["parse_mode"] == "HTML"
    assert events[0].payload == {
        "chat_id": -100,
        "user_id": 10,
        "username": "newuser",
    }


@pytest.mark.asyncio
async def test_handler_welcomes_humans_and_ignores_bots():
    welcomed = []

    class Service:
        async def welcome(self, chat_id, member):
            welcomed.append((chat_id, member.id))

    message = SimpleNamespace(
        chat=SimpleNamespace(id=-100),
        new_chat_members=(
            user(10),
            user(20, is_bot=True),
            user(30),
        ),
    )

    await welcome_new_members(message, Service())

    assert welcomed == [(-100, 10), (-100, 30)]
