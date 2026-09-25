"""Download selection callback."""

import asyncio
from aiogram import Router
from aiogram.types import CallbackQuery
from app.download.engine import DownloadEngine
from app.media.session import pop_selection

router = Router(name="download")

@router.callback_query(lambda query: query.data and query.data.startswith("quality:"))
async def quality_callback(query: CallbackQuery) -> None:
    selection = pop_selection(query.data.split(":", 1)[1])
    if selection is None:
        await query.answer("This selection expired. Send the URL again.", show_alert=True)
        return
    await query.answer("Starting download...")
    status = await query.message.answer("⬇️ Preparing download...")
    loop = asyncio.get_running_loop()
    last = {"text": ""}
    def progress(data: dict) -> None:
        if data.get("status") != "downloading": return
        total = data.get("total_bytes") or data.get("total_bytes_estimate")
        downloaded = data.get("downloaded_bytes", 0)
        speed = data.get("speed") or 0
        eta = data.get("eta")
        percent = downloaded / total * 100 if total else 0
        text = f"⬇️ Downloading...\\n\\n{percent:.1f}%\\n📦 {downloaded/1024/1024:.1f} MB"
        if total: text += f" / {total/1024/1024:.1f} MB"
        text += f"\\n⚡ {speed/1024/1024:.2f} MB/s"
        if eta is not None: text += f"\\n⏱ ETA: {eta}s"
        if text != last["text"]:
            last["text"] = text
            loop.call_soon_threadsafe(asyncio.create_task, status.edit_text(text))
    try:
        await DownloadEngine(progress_callback=progress).download(selection.url, selection.format_id)
        await status.edit_text("✅ Download complete.")
    except Exception as exc:
        await status.edit_text(f"❌ Download failed: {type(exc).__name__}: {exc}")
