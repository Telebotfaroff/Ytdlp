"""Short-lived in-memory media selections for callback workflows."""

from dataclasses import dataclass
from uuid import uuid4

@dataclass(frozen=True)
class MediaSelection:
    url: str
    format_id: str

_STORE: dict[str, MediaSelection] = {}

def create_selection(url: str, format_id: str) -> str:
    token = uuid4().hex[:12]
    _STORE[token] = MediaSelection(url, format_id)
    return token

def pop_selection(token: str) -> MediaSelection | None:
    return _STORE.pop(token, None)
