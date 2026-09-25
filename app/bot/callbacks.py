"""Callbacks for media action buttons."""

from aiogram import Router
from aiogram.types import CallbackQuery

router = Router(name="callbacks")


@router.callback_query(lambda query: query.data and query.data.startswith("media:"))
async def media_callback(query: CallbackQuery) -> None:
    action = query.data.split(":", 1)[1]
    labels = {
        "filename": "✏️ Custom filename will be handled in the download step.",
        "screenshots": "📸 Screenshot generation will be connected in a later step.",
        "trim": "✂️ Video trimming will be connected in a later step.",
    }
    await query.answer()
    await query.message.answer(labels.get(action, "Action not available yet."))


@router.callback_query(lambda query: query.data and query.data.startswith("quality:"))
async def quality_callback(query: CallbackQuery) -> None:
    _, format_id = query.data.split(":", 1)
    await query.answer(f"Selected format {format_id}")
    await query.message.answer("⬇️ Download engine will be connected in the next step.")
