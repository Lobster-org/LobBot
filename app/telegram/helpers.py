from aiogram.types import Message


async def smart_reply(
    message: Message,
    text: str,
    **kwargs,
):

    if message.chat.type in {
        "group",
        "supergroup",
    }:

        return await message.reply(
            text,
            **kwargs,
        )


    return await message.answer(
        text,
        **kwargs,
    )