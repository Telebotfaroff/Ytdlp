"""Short-lived in-memory media and processing selections."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

@dataclass(frozen=True)
class MediaSelection:
    url: str
    format_id: str

@dataclass(frozen=True)
class ProcessingSelection:
    file_path: Path
    user_id: int

_SELECTIONS: dict[str, MediaSelection] = {}
_PROCESSING: dict[str, ProcessingSelection] = {}

def create_selection(url: str, format_id: str) -> str:
    token = uuid4().hex[:12]
    _SELECTIONS[token] = MediaSelection(url, format_id)
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
