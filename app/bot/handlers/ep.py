"""Eporner search and download command."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from time import monotonic
from uuid import uuid4

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from eporner_api import Client, DownloadConfigRAW

from app.config.settings import settings
from app.upload.telegram import get_telegram_uploader

router = Router(name="eporner")
logger = logging.getLogger("ytdlp.eporner")

_RESULTS: dict[str, tuple[str, str, float]] = {}
_TTL = 3600


def _cleanup() -> None:
    now = monotonic()
    for token, (_, _, created) in list(_RESULTS.items()):
        if now - created > _TTL:
            _RESULTS.pop(token, None)


def _keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬇️ Download", callback_data=f"epdl:{token}")]
        ]
    )


@router.message(Command("ep"))
async def eporner_search(message: Message, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Usage: /ep <search query>\n\nExample: /ep demo")
        return

    status = await message.answer(f"🔎 Searching Eporner for: {query}")
    _cleanup()

    try:
        client = Client()
        stream = client.search_videos(
            query=query,
            sorting_gay="0",
            sorting_order="latest",
            sorting_low_quality="1",
            per_page=5,
            pages=1,
        )

        count = 0
        async for result in stream:
            video = result.unwrap()
            title = getattr(video, "title", None) or "Untitled"
            url = getattr(video, "url", None)
            thumbnail = getattr(video, "thumbnail", None)
            if not url:
                continue

            token = uuid4().hex[:12]
            _RESULTS[token] = (url, title, monotonic())
            count += 1

            caption = f"🎬 {title}"
            if thumbnail:
                try:
                    await message.answer_photo(
                        photo=thumbnail,
                        caption=caption,
                        reply_markup=_keyboard(token),
                    )
                except Exception:
                    await message.answer(caption, reply_markup=_keyboard(token))
            else:
                await message.answer(caption, reply_markup=_keyboard(token))

            if count >= 5:
                break

        if count == 0:
            await status.edit_text("❌ No Eporner results found.")
        else:
            await status.edit_text(f"✅ Found {count} result(s).")
    except Exception as exc:
        logger.exception("Eporner search failed")
        await status.edit_text(
            f"❌ Eporner search failed: {type(exc).__name__}: {exc}"
        )


@router.callback_query(lambda query: query.data and query.data.startswith("epdl:"))
async def eporner_download(query: CallbackQuery) -> None:
    token = query.data.split(":", 1)[1]
    entry = _RESULTS.get(token)
    if not entry:
        await query.answer("This result expired. Search again with /ep.", show_alert=True)
        return

    url, title, _ = entry
    _RESULTS.pop(token, None)
    await query.answer("Starting download...")
    status = await query.message.answer(f"⬇️ Downloading:\n{title}")

    try:
        settings.prepare_directories()
        before = {p.resolve() for p in settings.download_dir.iterdir() if p.is_file()}

        client = Client()
        video = await client.get_video(url, load_html=True, load_api=True)
        config = DownloadConfigRAW(
            quality="best",
            path=str(settings.download_dir),
            no_title=False,
        )
        await video.download(config, mode="mp4_h264")

        candidates = [
            p for p in settings.download_dir.iterdir()
            if p.is_file() and p.resolve() not in before
        ]
        if not candidates:
            raise FileNotFoundError("Eporner API finished without producing a file")

        file_path = max(candidates, key=lambda p: p.stat().st_mtime)

        if file_path.stat().st_size > settings.max_telegram_file_size:
            raise ValueError("Downloaded file is larger than the configured 2 GB Telegram limit.")

        await status.edit_text("📤 Uploading to Telegram...")
        await get_telegram_uploader().upload_document(
            chat_id=query.from_user.id,
            path=file_path,
            caption=file_path.name,
        )
        await status.edit_text(f"✅ Download complete.\n\n{file_path.name}")
    except Exception as exc:
        logger.exception("Eporner download failed")
        await status.edit_text(
            f"❌ Eporner download failed: {type(exc).__name__}: {exc}"
        )
