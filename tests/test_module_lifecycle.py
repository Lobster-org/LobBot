from types import SimpleNamespace

import pytest

from app.core.container import AppContainer, create_container
from app.modules.base import BaseModule
from app.modules.loader import ModuleLoader
from app.telegram.voice.lifecycle import VoiceLifecycle


class LifecycleModule(BaseModule):
    def __init__(self, name, calls, fail_shutdown=False):
        self.name = name
        self.calls = calls
        self.fail_shutdown = fail_shutdown
        self.containers = []

    async def setup(self, container, dispatcher):
        self.calls.append((self.name, "setup"))
        self.containers.append(container)

    async def startup(self, container):
        self.calls.append((self.name, "startup"))
        self.containers.append(container)

    async def shutdown(self, container):
        self.calls.append((self.name, "shutdown"))
        self.containers.append(container)

        if self.fail_shutdown:
            raise RuntimeError("shutdown failed")


def fake_container():
    return AppContainer(
        settings=SimpleNamespace(),
        mongodb=SimpleNamespace(),
        event_bus=SimpleNamespace(),
        database=object(),
        voice_service=object(),
    )


@pytest.mark.asyncio
async def test_lifecycle_hooks_run_once_and_receive_container():
    calls = []
    runtime = fake_container()
    loader = ModuleLoader()
    module = LifecycleModule("one", calls)
    loader.register(module)

    await loader.setup(runtime, object())
    await loader.setup(runtime, object())
    await loader.startup(runtime)
    await loader.startup(runtime)
    await loader.shutdown(runtime)
    await loader.shutdown(runtime)

    assert calls == [
        ("one", "setup"),
        ("one", "startup"),
        ("one", "shutdown"),
    ]
    assert module.containers == [runtime, runtime, runtime]


@pytest.mark.asyncio
async def test_shutdown_is_reverse_order_and_isolates_failures(caplog):
    calls = []
    runtime = fake_container()
    loader = ModuleLoader()
    loader.register(LifecycleModule("first", calls))
    loader.register(
        LifecycleModule("second", calls, fail_shutdown=True)
    )
    loader.register(LifecycleModule("third", calls))

    await loader.setup(runtime, object())
    await loader.startup(runtime)
    calls.clear()
    await loader.shutdown(runtime)

    assert calls == [
        ("third", "shutdown"),
        ("second", "shutdown"),
        ("first", "shutdown"),
    ]
    assert "Module shutdown failed" in caplog.text


def test_container_creation_does_not_initialize_runtime_resources():
    first = create_container()
    second = create_container()

    assert first is not second
    assert first.mongodb is second.mongodb
    assert first.event_bus is second.event_bus
    assert first.database is None
    assert first.voice_lifecycle is None
    assert first.voice_service is None


@pytest.mark.asyncio
async def test_voice_lifecycle_does_not_initialize_twice(monkeypatch):
    class Client:
        def __init__(self):
            self.start_calls = 0
            self.disconnect_calls = 0

        async def start(self):
            self.start_calls += 1

        async def get_me(self):
            return SimpleNamespace(id=1, username="voice")

        async def disconnect(self):
            self.disconnect_calls += 1

    class Calls:
        def __init__(self):
            self.start_calls = 0

        async def start(self):
            self.start_calls += 1

    client = Client()
    calls = Calls()
    creations = []

    def create_voice_client():
        creations.append(True)
        return client, calls

    monkeypatch.setattr(
        "app.telegram.voice.lifecycle.create_voice_client",
        create_voice_client,
    )
    lifecycle = VoiceLifecycle()

    await lifecycle.start()
    await lifecycle.start()
    await lifecycle.stop()
    await lifecycle.stop()

    assert len(creations) == 1
    assert client.start_calls == 1
    assert calls.start_calls == 1
    assert client.disconnect_calls == 1
