import logging
from types import SimpleNamespace

from app.telegram.errors import (
    GENERIC_ERROR_MESSAGE,
    global_error_handler,
)


class FakeMessage:

    def __init__(self, fail_response=False):
        self.chat = SimpleNamespace(
            id=-1001,
            type="supergroup",
        )
        self.from_user = SimpleNamespace(id=42)
        self.fail_response = fail_response
        self.responses = []

    async def reply(self, text):
        if self.fail_response:
            raise RuntimeError("Telegram response failed")
        self.responses.append(("reply", text))

    async def answer(self, text):
        if self.fail_response:
            raise RuntimeError("Telegram response failed")
        self.responses.append(("answer", text))


def error_event(message, exception):
    update = SimpleNamespace(
        event_type="message",
        message=message,
        edited_message=None,
        channel_post=None,
        edited_channel_post=None,
        callback_query=None,
    )

    return SimpleNamespace(
        update=update,
        exception=exception,
    )


async def test_error_handler_logs_exception_and_replies_safely(
    caplog,
):
    message = FakeMessage()

    try:
        raise ValueError("internal details")
    except ValueError as exception:
        event = error_event(message, exception)

    with caplog.at_level(logging.ERROR):
        handled = await global_error_handler(event)

    assert handled is True
    assert message.responses == [
        ("reply", GENERIC_ERROR_MESSAGE)
    ]
    assert "ValueError" in caplog.text
    assert "internal details" not in message.responses[0][1]


async def test_error_handler_does_not_escape_when_response_fails(
    caplog,
):
    message = FakeMessage(fail_response=True)
    event = error_event(
        message,
        RuntimeError("handler failed"),
    )

    with caplog.at_level(logging.ERROR):
        handled = await global_error_handler(event)

    assert handled is True
    assert "Failed to send safe error response" in caplog.text
