import logging
from typing import Any

from aiogram.types import ErrorEvent


logger = logging.getLogger(__name__)

GENERIC_ERROR_MESSAGE = (
    "Something went wrong while processing that request."
)


def _first_available(
    source: Any,
    *names: str,
):
    for name in names:
        value = getattr(source, name, None)
        if value is not None:
            return value

    return None


def error_context(update) -> tuple[
    str,
    int | None,
    int | None,
    Any,
    Any,
]:
    update_type = getattr(
        update,
        "event_type",
        None,
    ) or type(update).__name__
    callback = getattr(
        update,
        "callback_query",
        None,
    )
    message = _first_available(
        update,
        "message",
        "edited_message",
        "channel_post",
        "edited_channel_post",
    )

    if message is None and callback is not None:
        message = getattr(callback, "message", None)

    user = (
        getattr(callback, "from_user", None)
        if callback is not None
        else None
    ) or (
        getattr(message, "from_user", None)
        if message is not None
        else None
    )
    chat = (
        getattr(message, "chat", None)
        if message is not None
        else None
    )

    return (
        str(update_type),
        getattr(user, "id", None),
        getattr(chat, "id", None),
        message,
        callback,
    )


async def global_error_handler(
    event: ErrorEvent,
) -> bool:
    exception = event.exception
    (
        update_type,
        user_id,
        chat_id,
        message,
        callback,
    ) = error_context(event.update)

    logger.error(
        "Unhandled Telegram update error: "
        "update_type=%s user=%s chat=%s exception=%s",
        update_type,
        user_id,
        chat_id,
        type(exception).__name__,
        exc_info=(
            type(exception),
            exception,
            exception.__traceback__,
        ),
    )

    try:
        if callback is not None:
            await callback.answer(
                GENERIC_ERROR_MESSAGE,
                show_alert=True,
            )
        elif message is not None:
            if getattr(message.chat, "type", None) in {
                "group",
                "supergroup",
            }:
                await message.reply(
                    GENERIC_ERROR_MESSAGE
                )
            else:
                await message.answer(
                    GENERIC_ERROR_MESSAGE
                )
    except Exception:
        logger.exception(
            "Failed to send safe error response: "
            "update_type=%s user=%s chat=%s",
            update_type,
            user_id,
            chat_id,
        )

    return True


def register_error_handlers(dispatcher):
    dispatcher.errors.register(
        global_error_handler
    )
