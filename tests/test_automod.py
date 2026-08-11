from types import SimpleNamespace

import pytest

from app.core.events import EventBus
from app.core.permissions import Role
from app.modules.moderation.events import AUTOMOD_VIOLATION
from app.modules.moderation.models.automod import AutomodConfig
from app.modules.moderation.services.automod_service import AutomodService


class ConfigRepository:
    def __init__(self, config=None):
        self.config = config or {}
        self.saved = []

    async def get_config(self, chat_id):
        return self.config

    async def set_config(self, chat_id, config):
        self.config = config
        self.saved.append((chat_id, config))


class Moderation:
    def __init__(self):
        self.warned = []
        self.muted = []
        self.resolved = []
        self.count = 0

    async def warn(self, chat_id, user_id, moderator_id, reason):
        self.warned.append((chat_id, user_id, moderator_id, reason))
        self.count += 1

    async def warning_count(self, chat_id, user_id):
        return self.count

    async def mute(
        self,
        chat_id,
        user_id,
        moderator_id,
        duration_seconds,
        reason,
    ):
        self.muted.append(
            (chat_id, user_id, moderator_id, duration_seconds, reason)
        )

    async def resolve_warnings(self, chat_id, user_id, moderator_id):
        self.resolved.append((chat_id, user_id, moderator_id))
        self.count = 0


class Bot:
    id = 999

    def __init__(self):
        self.deleted = []

    async def delete_message(self, chat_id, message_id):
        self.deleted.append((chat_id, message_id))


class Permissions:
    def __init__(self, role=Role.MEMBER):
        self.role = role

    async def get_role(self, chat_id, user_id):
        return self.role


def build_automod(config=None):
    repository = ConfigRepository(config)
    moderation = Moderation()
    bot = Bot()
    bus = EventBus()
    service = AutomodService(repository, moderation, bot, bus)
    return service, repository, moderation, bot, bus


def message(text, message_id=10):
    return SimpleNamespace(
        text=text,
        caption=None,
        message_id=message_id,
        chat=SimpleNamespace(id=-100, type="supergroup"),
        from_user=SimpleNamespace(id=10, is_bot=False),
    )


@pytest.mark.asyncio
async def test_automod_configuration_is_persisted():
    service, repository, _, _, _ = build_automod()

    await service.set_enabled(-100, True)
    await service.set_rule(-100, "links", True)
    assert await service.add_word(-100, "Spoiler") is True
    assert await service.add_word(-100, "spoiler") is False

    config = await service.get_config(-100)
    assert config.enabled is True
    assert config.rules["links"] is True
    assert config.blocked_words == ["spoiler"]
    assert repository.saved


@pytest.mark.asyncio
async def test_blocked_word_deletes_warns_and_emits_event():
    config = AutomodConfig(
        enabled=True,
        rules={
            "flood": False,
            "repeat": False,
            "links": False,
            "caps": False,
            "words": True,
        },
        blocked_words=["spoiler"],
    ).to_document()
    service, _, moderation, bot, bus = build_automod(config)
    events = []

    async def record(event):
        events.append(event)

    bus.subscribe(AUTOMOD_VIOLATION, record)
    violation = await service.inspect_message(
        message("This contains a SpOiLeR."),
        Permissions(),
    )

    assert violation == "blocked_word"
    assert bot.deleted == [(-100, 10)]
    assert moderation.warned[0][3] == "Automod: blocked_word"
    assert events[0].payload["rule"] == "blocked_word"


@pytest.mark.asyncio
async def test_automod_exempts_lobbot_moderators_and_admins():
    config = AutomodConfig(enabled=True).to_document()
    service, _, moderation, bot, _ = build_automod(config)

    result = await service.inspect_message(
        message("message"),
        Permissions(Role.MODERATOR),
    )

    assert result is None
    assert moderation.warned == []
    assert bot.deleted == []


@pytest.mark.asyncio
async def test_automod_escalates_warning_threshold_to_temporary_mute():
    config = AutomodConfig(
        enabled=True,
        rules={
            "flood": False,
            "repeat": False,
            "links": True,
            "caps": False,
            "words": False,
        },
        warning_threshold=3,
        mute_duration_seconds=600,
    ).to_document()
    service, _, moderation, _, _ = build_automod(config)

    for index in range(3):
        await service.inspect_message(
            message(f"https://example.com/{index}", index + 1),
            Permissions(),
        )

    assert len(moderation.warned) == 3
    assert moderation.muted[0][3] == 600
    assert moderation.resolved == [(-100, 10, 999)]
    assert moderation.count == 0


@pytest.mark.asyncio
async def test_link_caps_repeat_and_flood_detectors():
    service, _, _, _, _ = build_automod()
    config = AutomodConfig()

    config.rules = {
        "flood": False,
        "repeat": False,
        "links": True,
        "caps": False,
        "words": False,
    }
    assert await service._detect(-100, 10, "visit https://x.test", config) == "link"

    config.rules["links"] = False
    config.rules["caps"] = True
    assert await service._detect(-100, 10, "THIS MESSAGE IS LOUD", config) == "caps"

    config.rules["caps"] = False
    config.rules["repeat"] = True
    assert await service._detect(-100, 11, "same", config) is None
    assert await service._detect(-100, 11, "same", config) is None
    assert await service._detect(-100, 11, "same", config) == "repeated_message"

    config.rules["repeat"] = False
    config.rules["flood"] = True
    config.flood_limit = 3
    assert await service._detect(-100, 12, "one", config) is None
    assert await service._detect(-100, 12, "two", config) is None
    assert await service._detect(-100, 12, "three", config) == "flood"
