"""Configurable multipart file uploader with progress reporting."""

from __future__ import annotations

import aiohttp
import asyncio
import json
import time
from pathlib import Path

class UploadError(RuntimeError):
    pass

class FileUploader:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    async def upload(self, path: Path, progress=None) -> str:
        if not path.is_file():
            raise FileNotFoundError(path)
        total = path.stat().st_size
        sent = 0
        started = time.monotonic()

        async def generator():
            nonlocal sent
            with path.open("rb") as handle:
                while True:
                    chunk = await asyncio.to_thread(handle.read, 1024 * 1024)
                    if not chunk:
                        break
                    sent += len(chunk)
                    elapsed = max(time.monotonic() - started, 0.001)
                    speed = sent / elapsed
                    eta = int((total - sent) / speed) if speed else None
                    if progress:
                        progress(sent, total, speed, eta)
                    yield chunk

        data = aiohttp.FormData()
        data.add_field("file", generator(), filename=path.name, content_type="application/octet-stream")
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=60, sock_read=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.endpoint, data=data) as response:
                body = await response.text()
                if response.status >= 400:
                    raise UploadError(f"HTTP {response.status}: {body[:500]}")
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError as exc:
                    raise UploadError("Uploader returned invalid JSON") from exc
        if payload.get("status") != "ok":
            raise UploadError(str(payload.get("message") or payload))
        result = payload.get("data") or {}
        link = result.get("downloadPage") or result.get("directLink")
        if not link:
            raise UploadError("Uploader response did not contain a download URL")
        return str(link)