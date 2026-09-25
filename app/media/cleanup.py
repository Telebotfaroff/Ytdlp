"""Temporary media storage cleanup helpers."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def cleanup_old_files(root: Path, max_age_seconds: int) -> int:
    if not root.exists():
        return 0
    now = time.time()
    removed = 0
    for path in list(root.iterdir()):
        try:
            if now - path.stat().st_mtime > max_age_seconds:
                remove_path(path)
                removed += 1
        except OSError:
            continue
    return removed


def cleanup_runtime_storage(download_dir: Path, temp_dir: Path, max_age_seconds: int) -> int:
    return cleanup_old_files(download_dir, max_age_seconds) + cleanup_old_files(temp_dir, max_age_seconds)
