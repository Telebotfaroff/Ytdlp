"""Automatic URL detection handler."""

import re

from aiogram import Router
from aiogram.types import Message

router = Router(name="url")
_URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


@router.message()
async def url_handler(message: Message) -> None:
    text = message.text or message.caption or ""
    match = _URL_RE.search(text)
    if not match:
        return
    url = match.group(0).rstrip(".,!?;:)]}")
    await message.answer(f"🔗 URL detected.\n\n{url}\n\nMedia extraction will be connected in the next step.")
