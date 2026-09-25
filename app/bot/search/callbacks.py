"""Pagination and quality-selection callbacks for search result cards."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import CallbackQuery, InputMediaPhoto

from app.bot.keyboards.search import quality_keyboard, result_keyboard
from app.bot.search.session import get_session
from app.media.resolver import MediaResolver
from app.media.session import create_selection

router = Router(name="search_callbacks")
logger = logging.getLogger("ytdlp.search_callbacks")


def _selector(height: int) -> str:
    return (
        f"bestvideo[height={height}]+bestaudio/"
        f"best[height={height}]/"
        f"bestvideo[height<={height}]+bestaudio/"
        f"best[height<={height}]"
    )


def _caption(session) -> str:
    result = session.results[session.index]
    return (
        f"🎬 {result.title}\n\n"
        f"🔎 {session.source}\n"
        f"📄 Result {session.index + 1} / {len(session.results)}"
    )


async def _render(query: CallbackQuery, token: str) -> None:
    session = get_session(token)
    if not session:
        return
    result = session.results[session.index]
    markup = result_keyboard(token, session.index, len(session.results))
    caption = _caption(session)

    try:
        if result.thumbnail:
            await query.message.edit_media(
                media=InputMediaPhoto(media=result.thumbnail, caption=caption),
                reply_markup=markup,
            )
        else:
            await query.message.edit_text(caption, reply_markup=markup)
    except Exception:
        try:
            await query.message.edit_caption(caption=caption, reply_markup=markup)
        except Exception:
            await query.message.edit_text(caption, reply_markup=markup)


@router.callback_query(lambda q: q.data and q.data.startswith(("srcprev:", "srcnext:")))
async def navigate(query: CallbackQuery) -> None:
    token = query.data.split(":", 1)[1]
    session = get_session(token)
    if not session or session.user_id != query.from_user.id:
        await query.answer("This search session expired.", show_alert=True)
        return

    if query.data.startswith("srcprev:"):
        if session.index == 0:
            await query.answer("Already at the first result.")
            return
        session.index -= 1
    else:
        if session.index >= len(session.results) - 1:
            await query.answer("Already at the last result.")
            return

        session.index += 1

    await query.answer()
    await _render(query, token)


@router.callback_query(lambda q: q.data and q.data.startswith("srcquality:"))
async def quality(query: CallbackQuery) -> None:
    token = query.data.split(":", 1)[1]
    session = get_session(token)
    if not session or session.user_id != query.from_user.id:
        await query.answer("This search session expired.", show_alert=True)
        return

    result = session.results[session.index]
    await query.answer("Checking qualities...")

    try:
        info = await MediaResolver().resolve(result.url)
        qualities = []
        seen = set()
        for fmt in sorted(
            [f for f in info.formats if f.has_video and f.height],
            key=lambda f: f.height or 0,
            reverse=True,
        ):
            height = int(fmt.height)
            if height in seen:
                continue
            seen.add(height)
            token = create_selection(result.url, _selector(height))
            qualities.append((f"⬇️ {height}p", f"quality:{token}"))

        if not qualities:
            token = create_selection(result.url, "best")
            qualities = [("⬇️ Download", f"quality:{token}")]

        filename_token = create_selection(result.url, "best")
        await query.message.edit_reply_markup(
            reply_markup=quality_keyboard(
                qualities,
                f"media:filename:{filename_token}",
            )
        )
    except Exception as exc:
        logger.exception("Quality resolution failed")
        token = create_selection(result.url, "best")
        filename_token = create_selection(result.url, "best")
        await query.message.edit_reply_markup(
            reply_markup=quality_keyboard(
                [("⬇️ Download", f"quality:{token}")],
                f"media:filename:{filename_token}",
            )
        )
