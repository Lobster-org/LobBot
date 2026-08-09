from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(
    Command(
        "start",
        ignore_case=True,
    )
)
async def start_command(
    message: Message,
    user_context,
):

    user = user_context["user"]

    group = user_context["group"]


    first_name = (
        user["first_name"]
        if user
        else "there"
    )


    if group:

        await message.reply(
            f"Hello {first_name}! 👋\n\n"
            f"This group has been registered "
            f"with LobBot."
        )

    else:

        await message.answer(
            f"Hello {first_name}! 👋\n\n"
            f"Your account has been registered."
        )