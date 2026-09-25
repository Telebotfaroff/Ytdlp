"""yt-dlp download engine with configurable external downloader support."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Any

import yt_dlp

from app.config.settings import settings

ProgressCallback = Callable[[dict[str, Any]], None]


class DownloadEngine:
    """Download selected media while exposing yt-dlp progress events."""

    def __init__(self, progress_callback: ProgressCallback | None = None) -> None:
        self.progress_callback = progress_callback

    def _download_sync(self, url: str, format_id: str, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        def hook(data: dict[str, Any]) -> None:
            if self.progress_callback:
                self.progress_callback(data)

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": format_id,
            "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
            "progress_hooks": [hook],
        }

        # yt-dlp can use aria2c when it is installed and explicitly enabled.
        # We keep this opt-in so unsupported environments still work with native HTTP.
        if settings.aria2_connections > 1:
            options["external_downloader"] = "aria2c"
            options["external_downloader_args"] = {
                "aria2c": [
                    "-x", str(settings.aria2_connections),
                    "-s", str(settings.aria2_split),
                    "-j", str(settings.aria2_max_concurrent),
                ]
            }

        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

    async def download(self, url: str, format_id: str, output_dir: Path | None = None) -> None:
        await asyncio.to_thread(self._download_sync, url, format_id, output_dir or settings.download_dir)
