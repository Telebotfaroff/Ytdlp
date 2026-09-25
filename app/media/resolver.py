"""yt-dlp based media metadata resolver."""

from __future__ import annotations

import asyncio
from typing import Any

import yt_dlp

from app.media.models import MediaFormat, MediaInfo


class MediaResolver:
    """Resolve webpage metadata and available media formats without downloading."""

    @staticmethod
    def _extract(url: str) -> dict[str, Any]:
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(url, download=False)

    async def resolve(self, url: str) -> MediaInfo:
        data = await asyncio.to_thread(self._extract, url)
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

        return MediaInfo(
            title=data.get("title") or "Unknown title",
            webpage_url=data.get("webpage_url") or url,
            thumbnail=data.get("thumbnail"),
            duration=data.get("duration"),
            uploader=data.get("uploader") or data.get("channel"),
            formats=formats,
        )
