"""Inline keyboards for media actions."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def media_keyboard(qualities: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    quality_row: list[InlineKeyboardButton] = []
    for label, callback_data in qualities:
        quality_row.append(InlineKeyboardButton(text=label, callback_data=callback_data))
        if len(quality_row) == 2:
            rows.append(quality_row)
            quality_row = []
    if quality_row:
        rows.append(quality_row)

    rows.extend([
        [InlineKeyboardButton(text="✏️ Custom Filename", callback_data="media:filename")],
        [
            InlineKeyboardButton(text="📸 Screenshots", callback_data="media:screenshots"),
            InlineKeyboardButton(text="✂️ Trim", callback_data="media:trim"),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
