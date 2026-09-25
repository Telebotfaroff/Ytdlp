"""Inline keyboards for paginated source search results."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def result_keyboard(
    session_token: str,
    index: int,
    total: int,
) -> InlineKeyboardMarkup:
    nav = []
    if index > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"srcprev:{session_token}",
            )
        )
    if index < total - 1:
        nav.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"srcnext:{session_token}",
            )
        )

    rows = [nav] if nav else []
    rows.append(
        [
            InlineKeyboardButton(
                text="⬇️ Download",
                callback_data=f"srcquality:{session_token}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quality_keyboard(
    qualities: list[tuple[str, str]],
    filename_callback: str,
) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for label, callback_data in qualities:
        row.append(InlineKeyboardButton(text=label, callback_data=callback_data))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="✏️ Custom Filename (Optional)",
                callback_data=filename_callback,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
