"""Download progress parsing helpers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadProgress:
    completed: int
    total: int | None
    speed: float | None
    eta: int | None

    @property
    def percent(self) -> float | None:
        if not self.total:
            return None
        return self.completed * 100 / self.total
