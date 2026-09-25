"""Large-file Telegram uploader backed by Pyrogram."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Callable

from pyrogram import Client


ProgressCallback = Callable[[int, int, float, int | None], None]


class TelegramUploadError(RuntimeError):
    pass


class TelegramUploader:
    def __init__(self, client: Client) -> None:
        self.client = client

    async def upload_document(
        self,
        chat_id: int,
        path: Path,
        caption: str | None = None,
        progress: ProgressCallback | None = None,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

        total = path.stat().st_size
        started = time.monotonic()
        loop = asyncio.get_running_loop()
        last = {"time": 0.0}

        def on_progress(current: int, total_bytes: int, *_args) -> None:
            now = time.monotonic()
            if now - last["time"] < 1.0 and current < total_bytes:
                return
            last["time"] = now
            elapsed = max(now - started, 0.001)
            speed = current / elapsed
            eta = int((total_bytes - current) / speed) if speed else None
            if progress:
                loop.call_soon_threadsafe(progress, current, total_bytes, speed, eta)

        try:
            return await self.client.send_document(
                chat_id=chat_id,
                document=str(path),
                caption=caption,
                progress=on_progress,
            )
        except Exception as exc:
            raise TelegramUploadError(f"Telegram upload failed: {type(exc).__name__}: {exc}") from exc
