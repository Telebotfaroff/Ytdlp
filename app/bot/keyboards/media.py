"""Inline keyboards for media selection."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def media_keyboard(
    qualities: list[tuple[str, str]],
    filename_callback: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    quality_row: list[InlineKeyboardButton] = []
    for label, callback_data in qualities:
        quality_row.append(
            InlineKeyboardButton(text=label, callback_data=callback_data)
        )
        if len(quality_row) == 2:
            rows.append(quality_row)
            quality_row = []

    if quality_row:
        rows.append(quality_row)

    # Custom filename is optional. The normal quality/download buttons above
    # remain usable without ever opening the filename prompt.
    rows.append([
        InlineKeyboardButton(
            text="✏️ Custom Filename (Optional)",
            callback_data=filename_callback,
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
