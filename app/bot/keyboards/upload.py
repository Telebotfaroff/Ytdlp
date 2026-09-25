"""Upload action keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def upload_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☁️ Upload to GoFile", callback_data=f"gofile:{token}")],
        [InlineKeyboardButton(text="📸 3 Screenshots", callback_data=f"shots:{token}:3"), InlineKeyboardButton(text="📸 6 Screenshots", callback_data=f"shots:{token}:6")],
        [InlineKeyboardButton(text="✂️ Trim", callback_data=f"trim:{token}")],
    ])
