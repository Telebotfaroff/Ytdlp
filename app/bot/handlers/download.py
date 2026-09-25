"""Download selection callback."""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Router
from aiogram.types import CallbackQuery

from app.download.engine import DownloadEngine

router = Router(name="download")


@router.callback_query(lambda query: query.data and query.data.startswith("quality:"))
async def quality_callback(query: CallbackQuery) -> None:
    format_id = query.data.split(":", 1)[1]
    await query.answer("Starting download...")
    status = await query.message.answer(f"⬇️ Downloading format `{format_id}`...", parse_mode="Markdown")

    last = {"text": ""}
    loop = asyncio.get_running_loop()

    def progress(data: dict) -> None:
        if data.get("status") != "downloading":
            return
        total = data.get("total_bytes") or data.get("total_bytes_estimate")
        downloaded = data.get("downloaded_bytes", 0)
        speed = data.get("speed")
        eta = data.get("eta")
        percent = (downloaded / total * 100) if total else 0
        speed_mb = (speed / 1024 / 1024) if speed else 0
        text = f"⬇️ Downloading...\\n\\n{percent:.1f}%\\n📦 {downloaded / 1024 / 1024:.1f} MB"
        if total:
            text += f" / {total / 1024 / 1024:.1f} MB"
        text += f"\\n⚡ {speed_mb:.2f} MB/s"
        if eta is not None:
            text += f"\\n⏱ ETA: {eta}s"
        if text == last["text"]:
            return
        last["text"] = text
        loop.call_soon_threadsafe(asyncio.create_task, status.edit_text(text))

    try:
        engine = DownloadEngine(progress_callback=progress)
        await engine.download(query.message.text or "", format_id, Path("./downloads"))
        await status.edit_text("✅ Download complete.")
    except Exception as exc:
        await status.edit_text(f"❌ Download failed: {type(exc).__name__}: {exc}")
