"""Short-lived in-memory media and processing selections."""

from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from uuid import uuid4

@dataclass(frozen=True)
class MediaSelection:
    url: str
    format_id: str
    filename: str | None = None

@dataclass(frozen=True)
class ProcessingSelection:
    file_path: Path
    user_id: int
    created_at: float

@dataclass(frozen=True)
class FilenamePending:
    url: str
    user_id: int
    created_at: float

_SELECTIONS: dict[str, MediaSelection] = {}
_PROCESSING: dict[str, ProcessingSelection] = {}
_FILENAME_PENDING: dict[int, FilenamePending] = {}

def create_selection(url: str, format_id: str, filename: str | None = None) -> str:
    token = uuid4().hex[:12]
    _SELECTIONS[token] = MediaSelection(url, format_id, filename, monotonic())
    return token

def pop_selection(token: str) -> MediaSelection | None:
    return _SELECTIONS.pop(token, None)

def create_processing(file_path: Path, user_id: int) -> str:
    token = uuid4().hex[:12]
    _PROCESSING[token] = ProcessingSelection(file_path, user_id, monotonic())
    return token

def get_processing(token: str) -> ProcessingSelection | None:
    return _PROCESSING.get(token)

def pop_processing(token: str) -> ProcessingSelection | None:
    return _PROCESSING.pop(token, None)

def get_user_processing(user_id: int) -> tuple[str, ProcessingSelection | None]:
    for token, selection in reversed(list(_PROCESSING.items())):
        if selection.user_id == user_id:
            return token, selection
    return "", None

def create_filename_request(url: str) -> str:
    token = uuid4().hex[:12]
    _SELECTIONS[token] = MediaSelection(url, "__filename__", None, monotonic())
    return token

def create_filename_pending(url: str, user_id: int) -> FilenamePending:
    pending = FilenamePending(url, user_id, monotonic())
    _FILENAME_PENDING[user_id] = pending
    return pending

def get_filename_pending(user_id: int) -> FilenamePending | None:
    return _FILENAME_PENDING.get(user_id)

def pop_filename_pending(user_id: int) -> FilenamePending | None:
    return _FILENAME_PENDING.pop(user_id, None)

def cleanup_expired(max_age_seconds: int) -> None:
    now = monotonic()
    for token, selection in list(_SELECTIONS.items()):\n        if now - selection.created_at > max_age_seconds:\n            _SELECTIONS.pop(token, None)
    for token, selection in list(_PROCESSING.items()):
        if now - selection.created_at > max_age_seconds:
            _PROCESSING.pop(token, None)
    for user_id, pending in list(_FILENAME_PENDING.items()):
        if now - pending.created_at > max_age_seconds:
            _FILENAME_PENDING.pop(user_id, None)
