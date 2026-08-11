import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.core.events import EventBus
from app.core.permissions import Permission, ROLE_PERMISSIONS, Role
from app.modules.moderation.commands import parse_duration
from app.modules.moderation.filters import can_moderate_target
from app.modules.moderation.events import (
    ACTION_CREATED,
    ACTION_REMOVED,
    MESSAGE_PURGED,
    USER_BANNED,
    USER_MUTED,
    USER_UNMUTED,
)
from app.modules.moderation.models.punishment import (
    Punishment,
    PunishmentStatus,
    PunishmentType,
)
from app.modules.moderation.services.moderation_service import (
    ModerationService,
)
from app.modules.moderation.services.punishment_service import (
    PunishmentService,
)


class Repository:
    def __init__(self):
        self.actions = []
        self.expired = []
        self.completed = []
        self.released = []

    async def create(self, action):
        action.id = f"action-{len(self.actions) + 1}"
        self.actions.append(action)
        return action

    async def get_warnings(self, chat_id, user_id):
        return [
            item
            for item in self.actions
            if item.chat_id == chat_id
            and item.user_id == user_id
            and item.action == PunishmentType.WARN
            and item.status == PunishmentStatus.ACTIVE
        ]

    async def count_warnings(self, chat_id, user_id):
        return len(await self.get_warnings(chat_id, user_id))

    async def remove_warning(self, chat_id, warning_id, removed_by):
        for item in self.actions:
            if item.id == warning_id and item.chat_id == chat_id:
                item.status = PunishmentStatus.REMOVED
                return item
        return None

    async def resolve_warnings(self, chat_id, user_id, resolved_by):
        warnings = await self.get_warnings(chat_id, user_id)
        for item in warnings:
            item.status = PunishmentStatus.EXPIRED
        return len(warnings)

    async def remove_active_action(
        self, chat_id, user_id, action, removed_by
    ):
        for item in reversed(self.actions):
            if (
                item.chat_id == chat_id
                and item.user_id == user_id
                and item.action == action
                and item.status == PunishmentStatus.ACTIVE
            ):
                item.status = PunishmentStatus.REMOVED
                return item
        return None

    async def claim_expired_mutes(self, now, limit):
        claimed = self.expired[:limit]
        self.expired = self.expired[limit:]
        return claimed

    async def complete_expiration(self, action_id):
        self.completed.append(action_id)

    async def release_expiration(self, action_id, error):
        self.released.append((action_id, error))


class Punishments:
    def __init__(self):
        self.muted = []
        self.unmuted = []
        self.banned = []
        self.unbanned = []
        self.purged = []
        self.unmute_error = None

    async def mute(self, chat_id, user_id, expires_at):
        self.muted.append((chat_id, user_id, expires_at))

    async def unmute(self, chat_id, user_id):
        if self.unmute_error:
            raise self.unmute_error
        self.unmuted.append((chat_id, user_id))

    async def ban(self, chat_id, user_id):
        self.banned.append((chat_id, user_id))

    async def unban(self, chat_id, user_id):
        self.unbanned.append((chat_id, user_id))

    async def purge(self, chat_id, message_ids):
        self.purged.append((chat_id, message_ids))
        return len(message_ids)


def build_service():
    repository = Repository()
    punishments = Punishments()
    bus = EventBus()
    service = ModerationService(
        repository,
        punishments,
        bus,
        poll_seconds=3600,
    )
    return service, repository, punishments, bus


def test_moderator_permissions_include_all_moderation_actions():
    permissions = ROLE_PERMISSIONS[Role.MODERATOR]
    assert {
        Permission.WARN_USERS,
        Permission.MUTE_USERS,
        Permission.PURGE_MESSAGES,
        Permission.VIEW_MOD_LOGS,
    } <= permissions
    assert Permission.BAN_USERS not in permissions


@pytest.mark.asyncio
async def test_manual_warning_creation_listing_and_removal():
    service, _, _, bus = build_service()
    events = []

    async def record(event):
        events.append(event.name)

    from app.modules.moderation.events import WARNING_CREATED

    bus.subscribe(WARNING_CREATED, record)
    warning = await service.warn(-100, 10, 20, "spam")

    assert await service.warning_count(-100, 10) == 1
    assert await service.warnings(-100, 10) == [warning]
    assert await service.remove_warning(-100, warning.id, 20) is warning
    assert await service.warning_count(-100, 10) == 0
    assert events == [WARNING_CREATED]


@pytest.mark.asyncio
async def test_moderation_role_hierarchy_protects_equal_and_higher_roles():
    class Permissions:
        roles = {
            1: Role.ADMIN,
            2: Role.MODERATOR,
            3: Role.MEMBER,
            4: Role.ADMIN,
            5: Role.OWNER,
        }

        async def get_role(self, chat_id, user_id):
            return self.roles[user_id]

    permissions = Permissions()

    assert await can_moderate_target(permissions, -100, 1, 2) is True
    assert await can_moderate_target(permissions, -100, 2, 3) is True
    assert await can_moderate_target(permissions, -100, 1, 4) is False
    assert await can_moderate_target(permissions, -100, 1, 5) is False


@pytest.mark.parametrize(
    ("value", "seconds"),
    [("10s", 10), ("5m", 300), ("2h", 7200), ("7d", 604800)],
)
def test_parse_duration(value, seconds):
    assert parse_duration(value) == seconds


@pytest.mark.parametrize("value", ["", "10", "1w", "0m", "366d"])
def test_parse_duration_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_duration(value)


@pytest.mark.asyncio
async def test_mute_records_expiration_and_emits_event():
    service, repository, punishments, bus = build_service()
    events = []

    async def record(event):
        events.append(event)

    bus.subscribe(USER_MUTED, record)
    before = datetime.now(timezone.utc)
    action = await service.mute(-100, 10, 20, 300, "flood")

    assert action in repository.actions
    assert action.expires_at >= before + timedelta(seconds=299)
    assert punishments.muted[0][:2] == (-100, 10)
    assert events[0].payload["action"] == "mute"


@pytest.mark.asyncio
async def test_manual_unmute_closes_mute_and_records_action():
    service, repository, punishments, bus = build_service()
    mute = await service.mute(-100, 10, 20, 300, "flood")
    events = []

    async def record(event):
        events.append((event.name, event.payload["action"]))

    for event_name in (ACTION_REMOVED, ACTION_CREATED, USER_UNMUTED):
        bus.subscribe(event_name, record)

    unmute = await service.unmute(-100, 10, 20)

    assert punishments.unmuted == [(-100, 10)]
    assert mute.status == PunishmentStatus.REMOVED
    assert unmute.action == PunishmentType.UNMUTE
    assert unmute in repository.actions
    assert events == [
        (ACTION_REMOVED, "mute"),
        (ACTION_CREATED, "unmute"),
        (USER_UNMUTED, "unmute"),
    ]


@pytest.mark.asyncio
async def test_mute_is_reverted_when_persistence_fails():
    service, repository, punishments, _ = build_service()

    async def fail_create(action):
        raise RuntimeError("database unavailable")

    repository.create = fail_create

    with pytest.raises(RuntimeError):
        await service.mute(-100, 10, 20, 300, "flood")

    assert punishments.muted[0][:2] == (-100, 10)
    assert punishments.unmuted == [(-100, 10)]


@pytest.mark.asyncio
async def test_expired_mute_is_unmuted_without_per_user_task():
    service, repository, punishments, bus = build_service()
    action = Punishment(
        id="expired-1",
        chat_id=-100,
        user_id=10,
        moderator_id=20,
        action=PunishmentType.MUTE,
        reason="flood",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    repository.expired.append(action)
    events = []

    async def record(event):
        events.append(event.name)

    bus.subscribe(USER_UNMUTED, record)
    bus.subscribe(ACTION_REMOVED, record)

    assert await service.process_expired_mutes() == 1
    assert punishments.unmuted == [(-100, 10)]
    assert repository.completed == ["expired-1"]
    assert events == [USER_UNMUTED, ACTION_REMOVED]


@pytest.mark.asyncio
async def test_failed_unmute_is_released_for_retry():
    service, repository, punishments, _ = build_service()
    action = Punishment(
        id="expired-1",
        chat_id=-100,
        user_id=10,
        moderator_id=20,
        action=PunishmentType.MUTE,
        reason="flood",
        created_at=datetime.now(timezone.utc),
    )
    repository.expired.append(action)
    punishments.unmute_error = RuntimeError("temporary failure")

    assert await service.process_expired_mutes() == 0
    assert repository.released[0][0] == "expired-1"


@pytest.mark.asyncio
async def test_ban_unban_and_purge_records_and_events():
    service, repository, punishments, bus = build_service()
    events = []

    async def record(event):
        events.append(event.name)

    for name in (USER_BANNED, ACTION_REMOVED, MESSAGE_PURGED):
        bus.subscribe(name, record)

    ban = await service.ban(-100, 10, 20, "raid")
    removed = await service.unban(-100, 10, 20)
    purge = await service.purge(-100, 20, [8, 9, 10])

    assert ban is removed
    assert punishments.banned == [(-100, 10)]
    assert punishments.unbanned == [(-100, 10)]
    assert punishments.purged == [(-100, [8, 9, 10])]
    assert purge.action.action == PunishmentType.PURGE
    assert purge.deleted_count == 3
    assert events == [USER_BANNED, ACTION_REMOVED, MESSAGE_PURGED]


@pytest.mark.asyncio
async def test_worker_start_and_stop_are_idempotent():
    service, _, _, _ = build_service()
    await service.start()
    first_task = service._expiration_task
    await service.start()

    assert service._expiration_task is first_task
    assert len(
        [
            task
            for task in asyncio.all_tasks()
            if task.get_name() == "moderation-expiration-worker"
        ]
    ) == 1

    await service.stop()
    await service.stop()
    assert service._expiration_task is None


@pytest.mark.asyncio
async def test_punishment_service_uses_telegram_api():
    class Bot:
        def __init__(self):
            self.calls = []

        async def restrict_chat_member(self, **kwargs):
            self.calls.append(("restrict", kwargs))

        async def get_chat(self, chat_id):
            return SimpleNamespace(permissions=None)

        async def ban_chat_member(self, **kwargs):
            self.calls.append(("ban", kwargs))

        async def unban_chat_member(self, **kwargs):
            self.calls.append(("unban", kwargs))

        async def delete_messages(self, **kwargs):
            self.calls.append(("purge", kwargs))

    bot = Bot()
    service = PunishmentService(bot)
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)

    await service.mute(-100, 10, expires)
    await service.unmute(-100, 10)
    await service.ban(-100, 10)
    await service.unban(-100, 10)
    await service.purge(-100, [1, 2])

    assert [name for name, _ in bot.calls] == [
        "restrict",
        "restrict",
        "ban",
        "unban",
        "purge",
    ]


@pytest.mark.asyncio
async def test_large_purge_uses_bulk_batches_of_at_most_100():
    class Bot:
        def __init__(self):
            self.batches = []

        async def delete_messages(self, **kwargs):
            self.batches.append(kwargs["message_ids"])
            return True

    bot = Bot()
    service = PunishmentService(bot)

    deleted = await service.purge(-100, list(range(1, 251)))

    assert deleted == 250
    assert sorted(len(batch) for batch in bot.batches) == [50, 100, 100]
    assert sorted(
        message_id
        for batch in bot.batches
        for message_id in batch
    ) == list(range(1, 251))


@pytest.mark.asyncio
async def test_reply_purge_deletes_inclusive_window_and_confirms():
    from app.modules.moderation.commands import purge_command

    class Service:
        def __init__(self):
            self.message_ids = None

        async def purge(self, chat_id, moderator_id, message_ids):
            self.message_ids = message_ids
            return SimpleNamespace(deleted_count=len(message_ids))

    answers = []

    async def answer(text, **kwargs):
        answers.append((text, kwargs))

    message = SimpleNamespace(
        text="/purge",
        message_id=250,
        reply_to_message=SimpleNamespace(message_id=101),
        chat=SimpleNamespace(id=-100, type="supergroup"),
        from_user=SimpleNamespace(id=20),
        answer=answer,
    )
    service = Service()

    await purge_command(message, service)

    assert service.message_ids == list(range(101, 251))
    assert "Deleted <b>150</b> messages" in answers[0][0]
    assert "s</b>" in answers[0][0]
