"""Upload action keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def upload_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☁️ Upload to GoFile", callback_data=f"gofile:{token}")],
    ])
