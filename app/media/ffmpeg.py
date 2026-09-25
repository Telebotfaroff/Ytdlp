"""FFmpeg helpers for screenshots, trimming, and Telegram-size splitting."""

from __future__ import annotations

import asyncio
import math
import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    """Raised when FFmpeg is unavailable or processing fails."""


def ensure_ffmpeg() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise FFmpegError("ffmpeg is not installed or not available on PATH")
    return binary


def _run(args: list[str]) -> None:
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise FFmpegError(str(exc)) from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown ffmpeg error"
        raise FFmpegError(detail)


def _duration(path: Path) -> float:
    probe = shutil.which("ffprobe")
    if not probe:
        raise FFmpegError("ffprobe is not installed or not available on PATH")
    result = subprocess.run(
        [probe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FFmpegError("Could not determine media duration")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise FFmpegError("Could not parse media duration") from exc


def screenshots(path: Path, output_dir: Path, count: int = 3) -> list[Path]:
    """Create evenly spaced JPEG screenshots without re-encoding the video."""
    ensure_ffmpeg()
    output_dir.mkdir(parents=True, exist_ok=True)
    duration = _duration(path)
    if duration <= 0:
        raise FFmpegError("Media has no usable duration")

    count = max(1, count)
    points = [(duration * i / (count + 1)) for i in range(1, count + 1)]
    results: list[Path] = []

    for index, point in enumerate(points, 1):
        target = output_dir / f"{path.stem}_shot_{index}.jpg"
        _run([
            "ffmpeg", "-y", "-ss", f"{point:.3f}", "-i", str(path),
            "-frames:v", "1", "-q:v", "3", str(target),
        ])
        results.append(target)

    return results


def trim(path: Path, output_path: Path, start: float, end: float) -> Path:
    """Trim using stream copy when possible, preserving the source streams."""
    ensure_ffmpeg()
    if start < 0 or end <= start:
        raise ValueError("Trim end must be greater than trim start")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y", "-ss", str(start), "-to", str(end),
        "-i", str(path), "-map", "0", "-c", "copy", str(output_path),
    ])
    return output_path


def split_for_telegram(path: Path, output_dir: Path, max_bytes: int) -> list[Path]:
    """Split a large media file into parts and verify every part is below the limit."""
    ensure_ffmpeg()
    if path.stat().st_size <= max_bytes:
        return [path]
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)
    duration = _duration(path)
    if duration <= 0:
        raise FFmpegError("Cannot split media with unknown duration")

    # Leave headroom for Telegram's size boundary and container overhead.
    target_bytes = int(max_bytes * 0.92)
    estimated_parts = max(2, math.ceil(path.stat().st_size / target_bytes))

    for attempt in range(5):
        parts = output_dir / f"{path.stem}_part_%03d{path.suffix}"
        for old in output_dir.glob(f"{path.stem}_part_*{path.suffix}"):
            old.unlink(missing_ok=True)

        segment_time = duration / estimated_parts
        _run([
            "ffmpeg", "-y", "-i", str(path),
            "-map", "0", "-c", "copy",
            "-f", "segment", "-segment_time", f"{segment_time:.3f}",
            "-reset_timestamps", "1", str(parts),
        ])

        created = sorted(output_dir.glob(f"{path.stem}_part_*{path.suffix}"))
        if created and all(p.stat().st_size <= max_bytes for p in created):
            return created

        estimated_parts *= 2

    raise FFmpegError("Could not split the media into Telegram-sized parts")


async def create_screenshots(path: Path, output_dir: Path, count: int = 3) -> list[Path]:
    return await asyncio.to_thread(screenshots, path, output_dir, count)


async def create_trim(path: Path, output_path: Path, start: float, end: float) -> Path:
    return await asyncio.to_thread(trim, path, output_path, start, end)


async def split_media(path: Path, output_dir: Path, max_bytes: int) -> list[Path]:
    return await asyncio.to_thread(split_for_telegram, path, output_dir, max_bytes)
