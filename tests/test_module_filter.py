from types import SimpleNamespace

import pytest

import app.telegram.filters as filters
from app.telegram.filters import CallbackModuleEnabled, ModuleEnabled


class DisabledModules:
    def __init__(self, database): pass
    async def is_enabled(self, chat_id, module_name): return False


@pytest.mark.asyncio
async def test_disabled_module_command_explains_how_to_enable(monkeypatch):
    monkeypatch.setattr(filters.container, "database", object())
    monkeypatch.setattr(filters, "ModuleService", DisabledModules)
    replies = []
    async def reply(text): replies.append(text)
    message = SimpleNamespace(
        text="/play song", chat=SimpleNamespace(id=-100, type="supergroup"),
        reply=reply,
    )

    assert await ModuleEnabled("music")(message) is False
    assert replies == [
        "This command isn't available because the music module is not enabled.\n"
        "An administrator can enable it with /enable music."
    ]


@pytest.mark.asyncio
async def test_disabled_passive_handler_does_not_reply(monkeypatch):
    monkeypatch.setattr(filters.container, "database", object())
    monkeypatch.setattr(filters, "ModuleService", DisabledModules)
    replies = []
    async def reply(text): replies.append(text)
    message = SimpleNamespace(
        text="12", chat=SimpleNamespace(id=-100, type="supergroup"), reply=reply,
    )

    assert await ModuleEnabled("games")(message) is False
    assert replies == []


@pytest.mark.asyncio
async def test_disabled_module_callback_explains_how_to_enable(monkeypatch):
    monkeypatch.setattr(filters.container, "database", object())
    monkeypatch.setattr(filters, "ModuleService", DisabledModules)
    answers = []
    async def answer(text, **kwargs): answers.append((text, kwargs))
    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=-100)), answer=answer,
    )

    assert await CallbackModuleEnabled("games")(callback) is False
    assert "/enable games" in answers[0][0]
    assert answers[0][1]["show_alert"] is True
