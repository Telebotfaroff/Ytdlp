"""Short-lived paginated search sessions."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from uuid import uuid4


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    thumbnail: str | None = None


@dataclass
class SearchSession:
    user_id: int
    source: str
    query: str
    results: list[SearchResult]
    index: int
    created_at: float


_SESSIONS: dict[str, SearchSession] = {}
_TTL = 3600


def create_session(user_id: int, source: str, query: str, results: list[SearchResult]) -> str:
    token = uuid4().hex[:12]
    _SESSIONS[token] = SearchSession(user_id, source, query, results, 0, monotonic())
    return token


def get_session(token: str) -> SearchSession | None:
    session = _SESSIONS.get(token)
    if session and monotonic() - session.created_at > _TTL:
        _SESSIONS.pop(token, None)
        return None
    return session


def delete_session(token: str) -> None:
    _SESSIONS.pop(token, None)


def cleanup() -> None:
    now = monotonic()
    for token, session in list(_SESSIONS.items()):
        if now - session.created_at > _TTL:
            _SESSIONS.pop(token, None)
