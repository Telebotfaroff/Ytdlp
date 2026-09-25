"""yt-dlp based media metadata resolver."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import yt_dlp

from app.media.models import MediaFormat, MediaInfo

logger = logging.getLogger("ytdlp.resolver")


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


class MediaResolver:
    """Resolve webpage metadata and available media formats without downloading."""

    @staticmethod
    def _extract(url: str) -> dict[str, Any]:
        options = {
            "quiet": True,
            "no_warnings": False,
            "skip_download": True,
            "noplaylist": True,
            "logger": _YtDlpLogger(),
        }
        logger.info("Resolving URL: %s", url)
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(url, download=False)

    async def resolve(self, url: str) -> MediaInfo:
        try:
            data = await asyncio.to_thread(self._extract, url)
        except Exception:
            logger.exception("Resolver failed for URL: %s", url)
            raise

        formats: list[MediaFormat] = []
        for item in data.get("formats") or []:
            formats.append(
                MediaFormat(
                    format_id=str(item.get("format_id", "")),
                    ext=item.get("ext"),
                    resolution=item.get("resolution"),
                    width=item.get("width"),
                    height=item.get("height"),
                    filesize=item.get("filesize") or item.get("filesize_approx"),
                    fps=item.get("fps"),
                    has_video=item.get("vcodec") not in (None, "none"),
                    has_audio=item.get("acodec") not in (None, "none"),
                )
            )

        info = MediaInfo(
            title=data.get("title") or "Unknown title",
            webpage_url=data.get("webpage_url") or url,
            thumbnail=data.get("thumbnail"),
            duration=data.get("duration"),
            uploader=data.get("uploader") or data.get("channel"),
            formats=formats,
        )
        logger.info("Resolved '%s' | %d formats | duration=%s", info.title, len(formats), info.duration)
        return info
