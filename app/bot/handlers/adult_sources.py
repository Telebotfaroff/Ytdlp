"""Separate search commands for Pornhub, MissAV and xHamster."""

from __future__ import annotations

import logging
from time import monotonic
from uuid import uuid4

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config.settings import settings
from app.upload.telegram import get_telegram_uploader

router = Router(name="adult_sources")
logger = logging.getLogger("ytdlp.adult_sources")

_RESULTS: dict[str, tuple[str, str, str, float]] = {}
_TTL = 3600
_LIMIT = 5


def _cleanup() -> None:
    now = monotonic()
    for token, (_, _, _, created) in list(_RESULTS.items()):
        if now - created > _TTL:
            _RESULTS.pop(token, None)


def _button(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬇️ Download", callback_data=f"srcdl:{token}")]
        ]
    )


async def _search(
    message: Message,
    query: str,
    source: str,
) -> None:
    status = await message.answer(f"🔎 Searching {source} for: {query}")
    _cleanup()

    try:
        if source == "Pornhub":
            from pornhub_api import Client
            stream = Client().search_videos(query)
        elif source == "MissAV":
            from missav_api import Client
            stream = Client().search(query, video_count=_LIMIT)
        else:
            from xhamster_api import Client
            stream = Client().search_videos(query, pages=1)

        count = 0
        async for result in stream:
            video = result.unwrap()
            title = getattr(video, "title", None) or "Untitled"
            url = getattr(video, "url", None)
            thumbnail = getattr(video, "thumbnail", None)

            if not url:
                continue

            token = uuid4().hex[:12]
            _RESULTS[token] = (source, url, title, monotonic())
            count += 1

            caption = f"🎬 {title}\n\nSource: {source}"
            markup = _button(token)

            if thumbnail:
                try:
                    await message.answer_photo(
                        photo=thumbnail,
                        caption=caption,
                        reply_markup=markup,
                    )
                except Exception:
                    await message.answer(caption, reply_markup=markup)
            else:
                await message.answer(caption, reply_markup=markup)

            if count >= _LIMIT:
                break

        await status.edit_text(
            f"✅ Found {count} result(s) on {source}."
            if count else
            f"❌ No results found on {source}."
        )
    except Exception as exc:
        logger.exception("%s search failed", source)
        await status.edit_text(
            f"❌ {source} search failed: {type(exc).__name__}: {exc}"
        )


@router.message(Command("ph"))
async def pornhub_search(message: Message, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Usage: /ph <search query>")
        return
    await _search(message, query, "Pornhub")


@router.message(Command("missav"))
async def missav_search(message: Message, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Usage: /missav <search query>")
        return
    await _search(message, query, "MissAV")


@router.message(Command("xh"))
async def xhamster_search(message: Message, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Usage: /xh <search query>")
        return
    await _search(message, query, "xHamster")


@router.callback_query(lambda query: query.data and query.data.startswith("srcdl:"))
async def source_download(query: CallbackQuery) -> None:
    token = query.data.split(":", 1)[1]
    entry = _RESULTS.get(token)

    if not entry:
        await query.answer("This result expired. Search again.", show_alert=True)
        return

    source, url, title, _ = entry
    _RESULTS.pop(token, None)

    await query.answer("Starting download...")
    status = await query.message.answer(f"⬇️ Downloading from {source}:\n{title}")

    try:
        settings.prepare_directories()
        before = {p.resolve() for p in settings.download_dir.iterdir() if p.is_file()}

        if source == "Pornhub":
            from pornhub_api import Client, DownloadConfigHLS
            video = await Client().get_video(url, load_html=True)
            config = DownloadConfigHLS(
                quality="best",
                path=str(settings.download_dir),
                no_title=False,
            )
            await video.download(config)
        elif source == "MissAV":
            from missav_api import Client, DownloadConfigHLS
            video = await Client().get_video(url, load_html=True)
            config = DownloadConfigHLS(
                quality="best",
                path=str(settings.download_dir),
                no_title=False,
            )
            await video.download(config)
        else:
            from xhamster_api import Client, DownloadConfigHLS
            video = await Client().get_video(url, load_html=True)
            config = DownloadConfigHLS(
                quality="best",
                path=str(settings.download_dir),
                no_title=False,
            )
            await video.download(config)

        candidates = [
            p for p in settings.download_dir.iterdir()
            if p.is_file() and p.resolve() not in before
        ]
        if not candidates:
            raise FileNotFoundError(
                f"{source} API finished without producing a file"
            )

        file_path = max(candidates, key=lambda p: p.stat().st_mtime)

        if file_path.stat().st_size > settings.max_telegram_file_size:
            raise ValueError(
                "Downloaded file is larger than the configured 2 GB Telegram limit."
            )

        await status.edit_text("📤 Uploading to Telegram...")
        await get_telegram_uploader().upload_document(
            chat_id=query.from_user.id,
            path=file_path,
            caption=file_path.name,
        )
        await status.edit_text(f"✅ Complete.\n\n{file_path.name}")
    except Exception as exc:
        logger.exception("%s download failed", source)
        await status.edit_text(
            f"❌ {source} download failed: {type(exc).__name__}: {exc}"
        )
