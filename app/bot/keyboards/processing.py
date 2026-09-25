"""Inline keyboard for downloaded-media processing."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def processing_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📸 3 Screenshots", callback_data=f"shots:{token}:3"),
            InlineKeyboardButton(text="📸 6 Screenshots", callback_data=f"shots:{token}:6"),
        ],
        [InlineKeyboardButton(text="✂️ Trim", callback_data=f"trim:{token}")],
    ])