"""Search command handler with one paginated result card."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from eporner_api import Client

from app.bot.keyboards.search import result_keyboard
from app.bot.search.session import SearchResult, cleanup, create_session

router = Router(name="eporner")
logger = logging.getLogger("ytdlp.eporner")
_LIMIT = 20


@router.message(Command("ep"))
async def search_handler(message: Message, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Usage: /ep <search query>")
        return

    status = await message.answer(f"🔎 Searching for: {query}")
    cleanup()

    try:
        stream = Client().search_videos(
            query=query,
            sorting_gay="0",
            sorting_order="latest",
            sorting_low_quality="1",
            per_page=_LIMIT,
            pages=1,
        )

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

        if not results:
            await status.edit_text("❌ No results found.")
            return

        token = create_session(message.from_user.id, "E", query, results)
        result = results[0]
        caption = f"🎬 {result.title}\n\n🔎 E\n📄 Result 1 / {len(results)}"
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
        logger.exception("Search failed")
        await status.edit_text(f"❌ Search failed: {type(exc).__name__}: {exc}")
