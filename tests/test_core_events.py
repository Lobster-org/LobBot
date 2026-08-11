from types import SimpleNamespace

import pytest

from app.core.event_names import (
    GROUP_REGISTERED,
    MODULE_DISABLED,
    MODULE_ENABLED,
    USER_REGISTERED,
)
from app.core.events import EventBus
from app.services.module_service import ModuleService
from app.services.user_service import UserService


class RegistrationRepository:
    def __init__(self, document):
        self.document = document
        self.calls = 0

    async def register_user(self, **values):
        self.calls += 1
        return self.document, self.calls == 1

    async def register_group(self, **values):
        self.calls += 1
        return self.document, self.calls == 1


class ModuleRepository:
    def __init__(self, modified_counts):
        self.modified_counts = iter(modified_counts)

    async def enable_module(self, group_id, module_name):
        return SimpleNamespace(
            modified_count=next(self.modified_counts)
        )

    async def disable_module(self, group_id, module_name):
        return SimpleNamespace(
            modified_count=next(self.modified_counts)
        )


@pytest.mark.asyncio
async def test_registration_events_emit_only_when_created():
    bus = EventBus()
    events = []

    async def record(event):
        events.append(event)

    bus.subscribe(USER_REGISTERED, record)
    bus.subscribe(GROUP_REGISTERED, record)

    users = RegistrationRepository({"telegram_id": 10})
    groups = RegistrationRepository({"telegram_id": -20})
    service = UserService(
        users=users,
        groups=groups,
        events=bus,
    )
    user = SimpleNamespace(
        id=10,
        username="lob",
        first_name="Lob",
        last_name=None,
    )
    group = SimpleNamespace(
        id=-20,
        title="Test Group",
        type="supergroup",
    )

    await service.register_user(user)
    await service.register_user(user)
    await service.register_group(group)
    await service.register_group(group)

    assert [event.name for event in events] == [
        USER_REGISTERED,
        GROUP_REGISTERED,
    ]
    assert events[0].payload == {
        "telegram_id": 10,
        "username": "lob",
        "first_name": "Lob",
    }
    assert events[1].payload["telegram_id"] == -20


@pytest.mark.asyncio
async def test_module_events_emit_only_for_database_changes():
    bus = EventBus()
    events = []

    async def record(event):
        events.append(event)

    bus.subscribe(MODULE_ENABLED, record)
    bus.subscribe(MODULE_DISABLED, record)
    service = ModuleService(
        repository=ModuleRepository([1, 0, 1]),
        events=bus,
    )

    assert await service.enable_module(-20, "music", 10) is True
    assert await service.enable_module(-20, "music", 10) is False
    assert await service.disable_module(-20, "music", 11) is True

    assert [event.name for event in events] == [
        MODULE_ENABLED,
        MODULE_DISABLED,
    ]
    assert events[0].payload == {
        "chat_id": -20,
        "module_name": "music",
        "changed_by": 10,
    }
    assert events[1].payload["changed_by"] == 11

