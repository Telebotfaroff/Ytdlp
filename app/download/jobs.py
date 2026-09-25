"""In-memory download job management for the current bot process."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from typing import Any
from uuid import uuid4


class DownloadCancelled(Exception):
    """Raised when a user cancels an active download."""


@dataclass
class DownloadJob:
    job_id: str
    user_id: int
    cancel_event: Event = field(default_factory=Event)
    task: Any = None

    def cancel(self) -> None:
        self.cancel_event.set()


_JOBS: dict[str, DownloadJob] = {}
_USER_JOBS: dict[int, str] = {}


def create_job(user_id: int) -> DownloadJob | None:
    """Create one active job per user."""
    existing = get_user_job(user_id)
    if existing is not None:
        return None

    job = DownloadJob(job_id=uuid4().hex[:12], user_id=user_id)
    _JOBS[job.job_id] = job
    _USER_JOBS[user_id] = job.job_id
    return job


def get_job(job_id: str) -> DownloadJob | None:
    return _JOBS.get(job_id)


def get_user_job(user_id: int) -> DownloadJob | None:
    job_id = _USER_JOBS.get(user_id)
    return _JOBS.get(job_id) if job_id else None


def remove_job(job_id: str) -> None:
    job = _JOBS.pop(job_id, None)
    if job is not None and _USER_JOBS.get(job.user_id) == job_id:
        _USER_JOBS.pop(job.user_id, None)
