"""Callbacks for screenshots, trimming, and custom filenames."""

from __future__ import annotations

import logging
import re

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.media import media_keyboard
from app.media.ffmpeg import create_screenshots, create_trim
from app.media.resolver import MediaResolver
from app.upload.gofile import GoFileUploader
from app.media.session import (
    create_selection,
    create_filename_pending,
    get_filename_pending,
    get_processing,
    pop_filename_pending,
    pop_selection,
)

router = Router(name="callbacks")
logger = logging.getLogger("ytdlp.callbacks")
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


def _format_selector(height: int) -> str:
    """Select a video height and merge separate audio when available."""
    return (
        f"bestvideo[height={height}]+bestaudio/"
        f"best[height={height}]/"
        f"bestvideo[height<={height}]+bestaudio/"
        f"best[height<={height}]"
    )


@router.callback_query(lambda q: q.data and q.data.startswith("media:filename:"))
async def filename_callback(query: CallbackQuery) -> None:
    token = query.data.split(":")[-1]
    selection = pop_selection(token)
    logger.info("Custom filename requested | user=%s | token=%s", query.from_user.id, token)
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
        logger.exception("Screenshot generation failed")
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
    user_id = message.from_user.id
    pending = get_filename_pending(user_id)

    if pending:
        logger.info("Custom filename received | user=%s | filename=%r", user_id, text)

        if not text:
            await message.answer("❌ Filename cannot be empty. Send the filename again.")
            return

        if len(text) > 180:
            await message.answer("❌ Filename must be 1-180 characters.")
            return

        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
        if not filename:
            await message.answer("❌ Invalid filename.")
            return

        pop_filename_pending(user_id)
        await message.answer("🔎 Preparing qualities for your custom filename...")

        try:
            logger.info("Resolving again for custom filename | user=%s | url=%s", user_id, pending.url)
            info = await MediaResolver().resolve(pending.url)

            qualities: list[tuple[str, str]] = []
            seen_heights: set[int] = set()
            for fmt in sorted(
                [f for f in info.formats if f.has_video and f.height],
                key=lambda f: f.height or 0,
                reverse=True,
            ):
                height = int(fmt.height)
                if height in seen_heights:
                    continue
                seen_heights.add(height)
                token = create_selection(pending.url, _format_selector(height), filename)
                qualities.append((f"⬇️ {height}p", f"quality:{token}"))

            if not qualities:
                # Direct media URLs can legitimately have no extractor format list.
                # Keep the custom filename flow usable instead of forcing a quality
                # that yt-dlp cannot discover.
                token = create_selection(pending.url, "best", filename)
                qualities.append(("⬇️ Download", f"quality:{token}"))

            logger.info(
                "Custom filename ready | user=%s | filename=%s | qualities=%d",
                user_id,
                filename,
                len(qualities),
            )
            await message.answer(
                f"✅ Filename set: {filename}\n\nChoose the quality:",
                reply_markup=media_keyboard(qualities, "media:noop"),
            )
        except Exception as exc:
            logger.exception("Custom filename preparation failed | user=%s", user_id)
            await message.answer(f"❌ Could not prepare custom filename: {type(exc).__name__}: {exc}")
        return

    if not _TRIM_RE.match(text):
        return

    from app.media.session import get_user_processing
    _, processing = get_user_processing(user_id)
    if not processing:
        return

    match = _TRIM_RE.match(text)
    start = _seconds(match.group(1))
    end = _seconds(match.group(2))
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
        logger.exception("Trim failed")
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
        text = (
            f"☁️ GoFile upload... {percent:.1f}%\n"
            f"📦 {sent / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB\n"
            f"⚡ {speed / 1024 / 1024:.2f} MB/s"
        )
        if eta is not None:
            text += f"\n⏱ ETA: {eta}s"
        import asyncio
        asyncio.create_task(status.edit_text(text))

    try:
        link = await GoFileUploader().upload(selection.file_path, progress=progress)
        await status.edit_text(f"✅ GoFile upload complete.\n\n{link}")
    except Exception as exc:
        logger.exception("GoFile upload failed")
        await status.edit_text(f"❌ GoFile upload failed: {type(exc).__name__}: {exc}")
