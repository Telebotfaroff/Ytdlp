"""Callbacks for media action buttons.

Quality callbacks live in the download router. This router handles only
media-processing actions that are not yet wired to an active downloaded file.
"""

from aiogram import Router
from aiogram.types import CallbackQuery

router = Router(name="callbacks")


@router.callback_query(lambda query: query.data and query.data.startswith("media:"))
async def media_callback(query: CallbackQuery) -> None:
    action = query.data.split(":", 1)[1]
    labels = {
        "filename": "✏️ Custom filename will be connected after the media-processing flow.",
        "screenshots": "📸 Screenshot processing is now available in the media processor.",
        "trim": "✂️ Trimming is now available in the media processor.",
    }
    await query.answer()
    await query.message.answer(labels.get(action, "Action not available yet."))
