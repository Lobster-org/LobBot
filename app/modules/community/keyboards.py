from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def verification_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Verify I'm Human",
                    callback_data=f"community:verify:{user_id}",
                )
            ]
        ]
    )
