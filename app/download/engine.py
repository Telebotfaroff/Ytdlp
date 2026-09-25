"""yt-dlp download engine with cancellation and result tracking."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from threading import Event
from typing import Callable, Any

import yt_dlp

from app.config.settings import settings
from app.download.jobs import DownloadCancelled

ProgressCallback = Callable[[dict[str, Any]], None]
logger = logging.getLogger("ytdlp.download")


class _YtDlpLogger:
    def debug(self, msg: str) -> None:
        if msg.startswith("[debug]"):
            logger.debug(msg)
        else:
            logger.info(msg)

    def info(self, msg: str) -> None:
        logger.info(msg)

    def warning(self, msg: str) -> None:
        logger.warning(msg)

    def error(self, msg: str) -> None:
        logger.error(msg)


class DownloadEngine:
    """Download selected media while exposing progress events."""

    def __init__(
        self,
        progress_callback: ProgressCallback | None = None,
        cancel_event: Event | None = None,
    ) -> None:
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event

    def _download_sync(self, url: str, format_id: str, output_dir: Path, filename: str | None = None) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        before = {p.resolve() for p in output_dir.iterdir() if p.is_file()}
        logger.info("Download requested | url=%s | format=%s | filename=%s", url, format_id, filename)

        def hook(data: dict[str, Any]) -> None:
            if self.cancel_event and self.cancel_event.is_set():
                raise DownloadCancelled()
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                downloaded = data.get("downloaded_bytes", 0)
                if total:
                    logger.info(
                        "Download progress %.1f%% | %.1f/%.1f MB | speed=%.2f MB/s | eta=%s",
                        downloaded / total * 100,
                        downloaded / 1024 / 1024,
                        total / 1024 / 1024,
                        (data.get("speed") or 0) / 1024 / 1024,
                        data.get("eta"),
                    )
            elif status == "finished":
                logger.info("yt-dlp finished: %s", data.get("filename"))
            if self.progress_callback:
                self.progress_callback(data)
            if self.cancel_event and self.cancel_event.is_set():
                raise DownloadCancelled()

        output_template = str(
            output_dir / ((filename + ".%(ext)s") if filename else "%(title)s.%(ext)s")
        )
        logger.info("Output template: %s", output_template)

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": False,
            "noplaylist": True,
            "format": format_id,
            "outtmpl": output_template,
            "progress_hooks": [hook],
            "logger": _YtDlpLogger(),
        }

        if settings.aria2_connections > 1:
            options["external_downloader"] = "aria2c"
            options["external_downloader_args"] = {
                "aria2c": [
                    "-x", str(settings.aria2_connections),
                    "-s", str(settings.aria2_split),
                    "-j", str(settings.aria2_max_concurrent),
                ]
            }
            logger.info(
                "aria2c enabled | connections=%s split=%s concurrent=%s",
                settings.aria2_connections,
                settings.aria2_split,
                settings.aria2_max_concurrent,
            )

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
        except DownloadCancelled:
            logger.warning("Download cancelled by user")
            raise
        except Exception:
            logger.exception("yt-dlp download failed")
            raise

        candidates = [
            p for p in output_dir.iterdir()
            if p.is_file() and p.resolve() not in before
        ]
        if not candidates:
            candidates = [p for p in output_dir.iterdir() if p.is_file()]

        if not candidates:
            logger.error("yt-dlp returned without a file")
            raise FileNotFoundError("yt-dlp finished without producing a media file")

        result = max(candidates, key=lambda p: p.stat().st_mtime)
        logger.info("Download result: %s (%d bytes)", result, result.stat().st_size)
        return result

    async def download(
        self,
        url: str,
        format_id: str,
        output_dir: Path | None = None,
        filename: str | None = None,
    ) -> Path:
        return await asyncio.to_thread(
            self._download_sync,
            url,
            format_id,
            output_dir or settings.download_dir,
            filename,
        )
