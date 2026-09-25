"""Callbacks for screenshots, trimming, and custom filenames."""

from __future__ import annotations

import re

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.media import media_keyboard\nfrom app.bot.keyboards.upload import upload_keyboard
from app.media.ffmpeg import create_screenshots, create_trim
from app.media.resolver import MediaResolver
from app.upload.gofile import GoFileUploader, UploadError
from app.media.session import (
    create_selection,
    create_filename_pending,
    get_filename_pending,
    get_processing,
    pop_filename_pending,
    pop_selection,
)

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


@router.callback_query(lambda q: q.data and q.data.startswith("media:filename:"))
async def filename_callback(query: CallbackQuery) -> None:
    token = query.data.split(":")[-1]
    selection = pop_selection(token)
    if not selection:
        await query.answer("This filename request expired.", show_alert=True)
        return
    await query.answer()
    create_filename_pending(selection.url, query.from_user.id)
    await query.message.answer("✏️ Send the custom filename without the extension.")


@router.callback_query(lambda q: q.data and q.data.startswith("media:"))
async def media_callback(query: CallbackQuery) -> None:
    await query.answer("Download the media first, then use its processing controls.")


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
    await query.message.answer("✂️ Send the trim range as two timestamps, for example: 00:30 02:00")


@router.message()
async def text_action_handler(message: Message) -> None:
    text = (message.text or "").strip()

    pending = get_filename_pending(message.from_user.id)
    if pending and text and not _TRIM_RE.match(text):
        if len(text) > 180:
            await message.answer("❌ Filename must be 1-180 characters.")
            return
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
        if not filename:
            await message.answer("❌ Invalid filename.")
            return

        pop_filename_pending(message.from_user.id)
        try:
            info = await MediaResolver().resolve(pending.url)
            qualities = []
            for height in sorted({f.height for f in info.formats if f.has_video and f.height}, reverse=True)[:12]:
                fmt = next(f for f in info.formats if f.has_video and f.height == height)
                token = create_selection(pending.url, fmt.format_id, filename)
                qualities.append((f"{height}p", f"quality:{token}"))
            await message.answer(
                "Choose the quality for your custom filename:",
                reply_markup=media_keyboard(qualities, "media:noop"),
            )
        except Exception as exc:
            await message.answer(f"❌ Could not prepare custom filename: {type(exc).__name__}: {exc}")
        return

    if not _TRIM_RE.match(text):
        return

    from app.media.session import get_user_processing
    _, processing = get_user_processing(message.from_user.id)
    if not processing:
        return

    start = _seconds(_TRIM_RE.match(text).group(1))
    end = _seconds(_TRIM_RE.match(text).group(2))
    if end <= start:
        await message.answer("❌ End time must be greater than start time.")
        return

    try:
        await message.answer("✂️ Trimming video with FFmpeg...")
        output = processing.file_path.parent / f"{processing.file_path.stem}_trimmed{processing.file_path.suffix}"
        result = await create_trim(processing.file_path, output, start, end)
        with result.open("rb") as video:
            await message.answer_document(video, caption=result.name)
        await message.answer("✅ Trim complete.")
    except Exception as exc:
        await message.answer(f"❌ Trim failed: {type(exc).__name__}: {exc}")


@router.callback_query(lambda q: q.data and q.data.startswith("gofile:"))
async def gofile_callback(query: CallbackQuery) -> None:
    token = query.data.split(":", 1)[1]
    selection = get_processing(token)
    if not selection or selection.user_id != query.from_user.id:
        await query.answer("This media session is unavailable.", show_alert=True)
        return

    await query.answer("Starting GoFile upload...")
    status = await query.message.answer("☁️ Uploading to GoFile...")

    last = {"time": 0.0}

    def progress(sent: int, total: int, speed: float, eta: int | None) -> None:
        import time
        now = time.monotonic()
        if now - last["time"] < 1.5 and sent < total:
            return
        last["time"] = now
        percent = sent / total * 100 if total else 0
        text = f"☁️ GoFile upload... {percent:.1f}%\n📦 {sent / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB\n⚡ {speed / 1024 / 1024:.2f} MB/s"
        if eta is not None:
            text += f"\n⏱ ETA: {eta}s"
        import asyncio
        asyncio.create_task(status.edit_text(text))

    try:
        link = await GoFileUploader().upload(selection.file_path, progress=progress)
        await status.edit_text(f"✅ GoFile upload complete.\n\n{link}")
    except Exception as exc:
        await status.edit_text(f"❌ GoFile upload failed: {type(exc).__name__}: {exc}")
