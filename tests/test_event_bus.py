import logging

import pytest

from app.core.events import EventBus


@pytest.mark.asyncio
async def test_subscribe_and_emit_passes_event_payload():
    bus = EventBus()
    received = []

    async def listener(event):
        received.append(event)

    assert bus.subscribe("test.created", listener) is True
    event = await bus.emit("test.created", {"value": 42})

    assert received == [event]
    assert event.name == "test.created"
    assert event.payload == {"value": 42}
    assert event.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_multiple_listeners_run_in_registration_order():
    bus = EventBus()
    calls = []

    async def first(event):
        calls.append(("first", event.name))

    async def second(event):
        calls.append(("second", event.name))

    bus.subscribe("test.ordered", first)
    bus.subscribe("test.ordered", second)

    await bus.emit("test.ordered")

    assert calls == [
        ("first", "test.ordered"),
        ("second", "test.ordered"),
    ]


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    bus = EventBus()
    calls = []

    async def listener(event):
        calls.append(event)

    bus.subscribe("test.removed", listener)
    assert bus.unsubscribe("test.removed", listener) is True
    assert bus.unsubscribe("test.removed", listener) is False

    await bus.emit("test.removed")

    assert calls == []
    assert bus.listener_count("test.removed") == 0


@pytest.mark.asyncio
async def test_broken_listener_does_not_block_other_listeners(caplog):
    bus = EventBus()
    calls = []

    async def broken(event):
        raise RuntimeError("listener failed")

    async def healthy(event):
        calls.append(event.name)

    bus.subscribe("test.failure", broken)
    bus.subscribe("test.failure", healthy)

    with caplog.at_level(logging.ERROR):
        await bus.emit("test.failure")

    assert calls == ["test.failure"]
    assert "Event listener failed" in caplog.text


def test_duplicate_subscription_is_ignored():
    bus = EventBus()

    async def listener(event):
        return None

    assert bus.subscribe("test.duplicate", listener) is True
    assert bus.subscribe("test.duplicate", listener) is False
    assert bus.listener_count("test.duplicate") == 1

