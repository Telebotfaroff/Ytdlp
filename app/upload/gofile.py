"""GoFile guest uploader."""

from __future__ import annotations

import aiohttp
import asyncio
import json
from pathlib import Path

from app.upload.uploader import UploadError, FileUploader

GOFILE_UPLOAD_ENDPOINT = "https://upload.gofile.io/uploadfile"


class GoFileUploader(FileUploader):
    """Upload directly to GoFile's guest endpoint."""

    def __init__(self) -> None:
        super().__init__(GOFILE_UPLOAD_ENDPOINT)

    async def upload(self, path: Path, progress=None) -> str:
        return await super().upload(path, progress=progress)
