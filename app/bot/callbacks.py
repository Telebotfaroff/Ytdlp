"""Callbacks for screenshots and trim processing."""

from __future__ import annotations

import re

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from app.media.ffmpeg import create_screenshots, create_trim
from app.media.session import get_processing

router = Router(name="callbacks")
_TRIM_RE = re.compile(r"^\s*(\d+(?::\d{1,2}){0,2})\s+([0-9]+(?::\d{1,2}){0,2})\s*$")


def _seconds(value: str) -> float:
    parts = [int(x) for x in value.split(":")]
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return float(parts[0] * 60 + parts[1])
    if len(parts) == 3:
        return float(parts[0] * 3600 + parts[1] * 60 + parts[2])
    raise ValueError("Invalid timestamp")


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
    await query.message.answer(
        "✂️ Send the trim range as two timestamps, for example: 00:30 02:00\n"
        "The first value is the start and the second is the end."
    )


@router.message()
async def trim_range_message(message: Message) -> None:
    text = message.text or ""
    match = _TRIM_RE.match(text)
    if not match:
        return

    # A timestamp pair is accepted only when the user has an active processing
    # session, so ordinary messages are not intercepted.
    # The most recent matching session for this user is found by inspecting the
    # in-memory processing store through the public helper.
    from app.media.session import get_user_processing
    selection_token, selection = get_user_processing(message.from_user.id)
    if not selection:
        return

    start = _seconds(match.group(1))
    end = _seconds(match.group(2))
    if end <= start:
        await message.answer("❌ End time must be greater than start time.")
        return

    try:
        await message.answer("✂️ Trimming video with FFmpeg...")
        output = selection.file_path.parent / f"{selection.file_path.stem}_trimmed{selection.file_path.suffix}"
        result = await create_trim(selection.file_path, output, start, end)
        await message.answer_document(result.open("rb"), caption=result.name)
        await message.answer("✅ Trim complete.")
    except Exception as exc:
        await message.answer(f"❌ Trim failed: {type(exc).__name__}: {exc}")
