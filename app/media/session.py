"""Short-lived in-memory media and processing selections."""

from dataclasses import dataclass
from pathlib import Path
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

_SELECTIONS: dict[str, MediaSelection] = {}
_PROCESSING: dict[str, ProcessingSelection] = {}

def create_selection(url: str, format_id: str, filename: str | None = None) -> str:
    token = uuid4().hex[:12]
    _SELECTIONS[token] = MediaSelection(url, format_id, filename)
    return token

def pop_selection(token: str) -> MediaSelection | None:
    return _SELECTIONS.pop(token, None)

def create_processing(file_path: Path, user_id: int) -> str:
    token = uuid4().hex[:12]
    _PROCESSING[token] = ProcessingSelection(file_path, user_id)
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
    _SELECTIONS[token] = MediaSelection(url, "__filename__")
    return token


@dataclass(frozen=True)
class FilenamePending:
    url: str
    user_id: int

_FILENAME_PENDING: dict[int, FilenamePending] = {}

def create_filename_pending(url: str, user_id: int) -> FilenamePending:
    pending = FilenamePending(url, user_id)
    _FILENAME_PENDING[user_id] = pending
    return pending

def get_filename_pending(user_id: int) -> FilenamePending | None:
    return _FILENAME_PENDING.get(user_id)

def pop_filename_pending(user_id: int) -> FilenamePending | None:
    return _FILENAME_PENDING.pop(user_id, None)
