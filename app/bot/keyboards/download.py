"""Keyboards used while downloading media."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cancel_download_keyboard(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel Download", callback_data=f"cancel:{job_id}")]
        ]
    )
