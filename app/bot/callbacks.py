"""Callbacks for screenshots and trim setup."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from app.media.ffmpeg import create_screenshots
from app.media.session import get_processing

router = Router(name="callbacks")

@router.callback_query(lambda q: q.data and q.data.startswith("media:"))
async def media_callback(query: CallbackQuery) -> None:
    await query.answer()
    await query.message.answer("Download the media first, then use its processing controls.")

@router.callback_query(lambda q: q.data and q.data.startswith("shots:"))
async def screenshots_callback(query: CallbackQuery) -> None:
    parts = query.data.split(":")
    if len(parts) != 3:
        await query.answer("Invalid screenshot request.", show_alert=True)
        return
    token, count_text = parts[1], parts[2]
    selection = get_processing(token)
    if not selection or selection.user_id != query.from_user.id:
        await query.answer("This media session is unavailable.", show_alert=True)
        return
    try:
        count = int(count_text)
        await query.answer("Generating screenshots...")
        output_dir = selection.file_path.parent / f"{selection.file_path.stem}_screenshots"
        images = await create_screenshots(selection.file_path, output_dir, count)
        for image in images:
            with image.open("rb") as photo:
                await query.message.answer_photo(photo)
        await query.message.answer(f"✅ Generated {len(images)} screenshots.")
    except Exception as exc:
        await query.message.answer(f"❌ Screenshot generation failed: {type(exc).__name__}: {exc}")

@router.callback_query(lambda q: q.data and q.data.startswith("trim:"))
async def trim_callback(query: CallbackQuery) -> None:
    token = query.data.split(":", 1)[1]
    selection = get_processing(token)
    if not selection or selection.user_id != query.from_user.id:
        await query.answer("This media session is unavailable.", show_alert=True)
        return
    await query.answer()
    await query.message.answer("✂️ Send the trim range as two timestamps, for example: 00:30 02:00\nThe first value is the start and the second is the end.")