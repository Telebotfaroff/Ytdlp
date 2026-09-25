"""Automatic URL detection handler."""

import re

from aiogram import Router
from aiogram.types import Message

from app.bot.keyboards.media import media_keyboard
from app.media.resolver import MediaResolver
from app.media.session import create_filename_request, create_selection

router = Router(name="url")
_URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_resolver = MediaResolver()


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "Unknown"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _quality_lines(info) -> list[str]:
    heights = sorted(
        {int(f.height) for f in info.formats if f.has_video and f.height},
        reverse=True,
    )
    return [f"• {height}p" for height in heights[:12]]


def _format_selector(height: int) -> str:
    # Select the requested video height and merge audio when the site exposes
    # video/audio as separate streams. Fall back to a combined stream.
    return (
        f"bestvideo[height={height}]+bestaudio/"
        f"best[height={height}]/"
        f"bestvideo[height<={height}]+bestaudio/"
        f"best[height<={height}]"
    )


@router.message()
async def url_handler(message: Message) -> None:
    text = message.text or message.caption or ""
    match = _URL_RE.search(text)
    if not match:
        return

    url = match.group(0).rstrip(".,!?;:)]}")
    status = await message.answer("🔎 Resolving media information...")

    try:
        info = await _resolver.resolve(url)
    except Exception as exc:
        await status.edit_text(
            f"❌ Could not resolve this URL.\n\n{type(exc).__name__}: {exc}"
        )
        return

    heights = sorted(
        {int(f.height) for f in info.formats if f.has_video and f.height},
        reverse=True,
    )

    details = [
        f"🎬 {info.title}",
        "",
        f"⏱ Duration: {_format_duration(info.duration)}",
    ]
    if info.uploader:
        details.append(f"👤 Uploader: {info.uploader}")

    if heights:
        details += [
            "",
            "Available qualities:",
            "\n".join(_quality_lines(info)),
        ]
    else:
        details += [
            "",
            "⚡ Direct download",
            "The source did not expose quality metadata.",
        ]

    quality_buttons: list[tuple[str, str]] = []

    if heights:
        for height in heights[:12]:
            token = create_selection(url, _format_selector(height))
            quality_buttons.append((f"⬇️ {height}p", f"quality:{token}"))
    else:
        # Important: a direct media URL may have no extractor format list.
        # Still give the user a download action instead of forcing the optional
        # filename flow.
        token = create_selection(url, "best")
        quality_buttons.append(("⬇️ Download", f"quality:{token}"))

    filename_token = create_filename_request(url)

    await status.edit_text(
        "\n".join(details),
        reply_markup=media_keyboard(
            quality_buttons,
            f"media:filename:{filename_token}",
        ),
    )
