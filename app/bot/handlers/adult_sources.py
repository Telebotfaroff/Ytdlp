"""Search command handlers using one paginated result card."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.bot.keyboards.search import result_keyboard
from app.bot.search.session import SearchResult, cleanup, create_session

router = Router(name="source_search")
logger = logging.getLogger("ytdlp.source_search")
_LIMIT = 20


async def _collect(query: str, source: str) -> list[SearchResult]:
    if source == "PH":
        from pornhub_api import Client
        stream = Client().search_videos(query)
    elif source == "M":
        from missav_api import Client
        stream = Client().search(query, video_count=_LIMIT)
    else:
        from xhamster_api import Client
        stream = Client().search_videos(query, pages=1)

    results = []
    async for item in stream:
        video = item.unwrap()
        url = getattr(video, "url", None)
        if not url:
            continue
        results.append(
            SearchResult(
                title=getattr(video, "title", None) or "Untitled",
                url=url,
                thumbnail=getattr(video, "thumbnail", None),
            )
        )
        if len(results) >= _LIMIT:
            break
    return results


async def _search(message: Message, command: CommandObject, source: str) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Please provide a search query.")
        return

    status = await message.answer(f"🔎 Searching for: {query}")
    cleanup()

    try:
        results = await _collect(query, source)
        if not results:
            await status.edit_text("❌ No results found.")
            return

        token = create_session(message.from_user.id, source, query, results)
        result = results[0]
        caption = f"🎬 {result.title}\n\n🔎 {source}\n📄 Result 1 / {len(results)}"
        markup = result_keyboard(token, 0, len(results))

        if result.thumbnail:
            try:
                await message.answer_photo(photo=result.thumbnail, caption=caption, reply_markup=markup)
            except Exception:
                await message.answer(caption, reply_markup=markup)
        else:
            await message.answer(caption, reply_markup=markup)

        await status.edit_text(f"✅ Found {len(results)} result(s).")
    except Exception as exc:
        logger.exception("%s search failed", source)
        await status.edit_text(f"❌ Search failed: {type(exc).__name__}: {exc}")


@router.message(Command("ph"))
async def ph_search(message: Message, command: CommandObject) -> None:
    await _search(message, command, "PH")


@router.message(Command("missav"))
async def missav_search(message: Message, command: CommandObject) -> None:
    await _search(message, command, "M")


@router.message(Command("xh"))
async def xh_search(message: Message, command: CommandObject) -> None:
    await _search(message, command, "XH")
