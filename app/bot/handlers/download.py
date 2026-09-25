"""Download selection, cancellation, processing, and Telegram upload callbacks."""

from __future__ import annotations

import asyncio
import time
import logging

from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.download import cancel_download_keyboard
from app.bot.keyboards.upload import upload_keyboard
from app.config.settings import settings
from app.download.engine import DownloadEngine
from app.download.jobs import DownloadCancelled, create_job, get_job, remove_job
from app.media.ffmpeg import split_media
from app.media.session import create_processing, pop_selection
from app.upload.telegram import get_telegram_uploader

router = Router(name="download")
logger = logging.getLogger("ytdlp.telegram")


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


def _upload_progress_text(sent: int, total: int, speed: float, eta: int | None) -> str:
    percent = sent / total * 100 if total else 0
    text = (
        f"📤 Uploading to Telegram...\n\n"
        f"{percent:.1f}%\n"
        f"📦 {sent / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB\n"
        f"⚡ {speed / 1024 / 1024:.2f} MB/s"
    )
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

    logger.info("Download started | user=%s | url=%s | format=%s | filename=%s", user_id, selection.url, selection.format_id, selection.filename)
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
            logger.info("Download worker running | user=%s | job=%s", user_id, job.job_id)
            file_path = await DownloadEngine(
                progress_callback=progress,
                cancel_event=job.cancel_event,
            ).download(selection.url, selection.format_id, filename=selection.filename)

            if job.cancel_event.is_set():
                raise DownloadCancelled()

            file_size = file_path.stat().st_size
            if file_size > settings.max_telegram_file_size:
                await status.edit_text("🧩 File is larger than Telegram's 2 GB bot limit. Splitting...")
                parts = await split_media(
                    file_path,
                    settings.temp_dir / f"parts_{job.job_id}",
                    settings.max_telegram_file_size,
                )
            else:
                parts = [file_path]

            uploader = get_telegram_uploader()
            last_upload_update = {"time": 0.0}

            for index, part in enumerate(parts, 1):
                if job.cancel_event.is_set():
                    raise DownloadCancelled()

                caption = part.name if len(parts) == 1 else f"{part.name} ({index}/{len(parts)})"

                def upload_progress(sent: int, total: int, speed: float, eta: int | None) -> None:
                    now = time.monotonic()
                    if now - last_upload_update["time"] < 1.5 and sent < total:
                        return
                    last_upload_update["time"] = now
                    loop.call_soon_threadsafe(
                        asyncio.create_task,
                        status.edit_text(_upload_progress_text(sent, total, speed, eta)),
                    )

                await uploader.upload_document(
                    chat_id=user_id,
                    path=part,
                    caption=caption,
                    progress=upload_progress,
                )

            logger.info("Upload complete | user=%s | job=%s | file=%s", user_id, job.job_id, file_path)
            token = create_processing(file_path, user_id)
            await status.edit_text(
                "✅ Upload complete.\n\nChoose an action:",
                reply_markup=upload_keyboard(token),
            )

        except DownloadCancelled:
            logger.info("Download cancelled | user=%s | job=%s", user_id, job.job_id)
            await status.edit_text("🛑 Download cancelled.")
        except Exception as exc:
            logger.exception("Download failed | user=%s | job=%s", user_id, job.job_id)
            await status.edit_text(
                f"❌ Download/processing/upload failed: {type(exc).__name__}: {exc}"
            )
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
