"""Download selection, cancellation, processing, and Telegram upload callbacks."""

from __future__ import annotations

import asyncio
import time

from aiogram import Router
from aiogram.types import CallbackQuery, FSInputFile

from app.bot.keyboards.download import cancel_download_keyboard
from app.bot.keyboards.processing import processing_keyboard
from app.config.settings import settings
from app.download.engine import DownloadEngine
from app.download.jobs import DownloadCancelled, create_job, get_job, remove_job
from app.media.ffmpeg import split_media
from app.media.session import create_processing, pop_selection

router = Router(name="download")


def _progress_text(data: dict) -> str:
    total = data.get("total_bytes") or data.get("total_bytes_estimate")
    downloaded = data.get("downloaded_bytes", 0)
    speed = data.get("speed") or 0
    eta = data.get("eta")

    percent = downloaded / total * 100 if total else 0
    text = f"⬇️ Downloading...\n\n{percent:.1f}%\n📦 {downloaded / 1024 / 1024:.1f} MB"
    if total:
        text += f" / {total / 1024 / 1024:.1f} MB"
    text += f"\n⚡ {speed / 1024 / 1024:.2f} MB/s"
    if eta is not None:
        text += f"\n⏱ ETA: {eta}s"
    return text


@router.callback_query(lambda query: query.data and query.data.startswith("quality:"))
async def quality_callback(query: CallbackQuery) -> None:
    selection = pop_selection(query.data.split(":", 1)[1])
    if selection is None:
        await query.answer("This selection expired. Send the URL again.", show_alert=True)
        return

    user_id = query.from_user.id
    job = create_job(user_id)
    if job is None:
        await query.answer("You already have a download running.", show_alert=True)
        return

    await query.answer("Starting download...")
    status = await query.message.answer(
        "⬇️ Preparing download...",
        reply_markup=cancel_download_keyboard(job.job_id),
    )

    loop = asyncio.get_running_loop()
    last_update = {"time": 0.0, "text": ""}

    def progress(data: dict) -> None:
        if data.get("status") != "downloading":
            return
        if job.cancel_event.is_set():
            raise DownloadCancelled()

        text = _progress_text(data)
        now = time.monotonic()
        if text == last_update["text"] or now - last_update["time"] < 1.5:
            return
        last_update["time"] = now
        last_update["text"] = text
        loop.call_soon_threadsafe(
            asyncio.create_task,
            status.edit_text(
                text,
                reply_markup=cancel_download_keyboard(job.job_id),
            ),
        )

    async def run_download() -> None:
        try:
            file_path = await DownloadEngine(
                progress_callback=progress,
                cancel_event=job.cancel_event,
            ).download(selection.url, selection.format_id)

            if job.cancel_event.is_set():
                raise DownloadCancelled()

            file_size = file_path.stat().st_size
            if file_size > settings.max_telegram_file_size:
                await status.edit_text("🧩 Large file detected. Splitting for Telegram...")
                parts = await split_media(
                    file_path,
                    settings.temp_dir / f"parts_{job.job_id}",
                    settings.max_telegram_file_size,
                )
            else:
                parts = [file_path]

            await status.edit_text(
                f"📤 Uploading {len(parts)} file{'s' if len(parts) != 1 else ''} to Telegram..."
            )

            for index, part in enumerate(parts, 1):
                if job.cancel_event.is_set():
                    raise DownloadCancelled()
                caption = part.name if len(parts) == 1 else f"{part.name} ({index}/{len(parts)})"
                await query.message.answer_document(
                    FSInputFile(part),
                    caption=caption,
                )

            await status.edit_text("✅ Download, processing, and upload complete.")

        except DownloadCancelled:
            await status.edit_text("🛑 Download cancelled.")
        except Exception as exc:
            await status.edit_text(f"❌ Download/processing/upload failed: {type(exc).__name__}: {exc}")
        finally:
            remove_job(job.job_id)

    job.task = asyncio.create_task(run_download())


@router.callback_query(lambda query: query.data and query.data.startswith("cancel:"))
async def cancel_callback(query: CallbackQuery) -> None:
    job_id = query.data.split(":", 1)[1]
    job = get_job(job_id)
    if job is None:
        await query.answer("This download is no longer active.", show_alert=True)
        return

    if job.user_id != query.from_user.id:
        await query.answer("This download belongs to another user.", show_alert=True)
        return

    job.cancel()
    await query.answer("Cancellation requested.")
