"""yt-dlp download engine with cancellation and result tracking."""

from __future__ import annotations

import asyncio
from pathlib import Path
from threading import Event
from typing import Callable, Any

import yt_dlp

from app.config.settings import settings
from app.download.jobs import DownloadCancelled

ProgressCallback = Callable[[dict[str, Any]], None]


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

        def hook(data: dict[str, Any]) -> None:
            if self.cancel_event and self.cancel_event.is_set():
                raise DownloadCancelled()
            if self.progress_callback:
                self.progress_callback(data)
            if self.cancel_event and self.cancel_event.is_set():
                raise DownloadCancelled()

        output_template = str(output_dir / ((filename + ".%(ext)s") if filename else "%(title)s.%(ext)s"))

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": format_id,
            "outtmpl": output_template,
            "progress_hooks": [hook],
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

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])
        except DownloadCancelled:
            raise

        candidates = [
            p for p in output_dir.iterdir()
            if p.is_file() and p.resolve() not in before
        ]
        if not candidates:
            # Some post-processing can replace an existing path. Fall back to
            # the newest regular file in the download directory.
            candidates = [p for p in output_dir.iterdir() if p.is_file()]

        if not candidates:
            raise FileNotFoundError("yt-dlp finished without producing a media file")

        return max(candidates, key=lambda p: p.stat().st_mtime)

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
