"""Media metadata models."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MediaFormat:
    format_id: str
    ext: str | None = None
    resolution: str | None = None
    width: int | None = None
    height: int | None = None
    filesize: int | None = None
    fps: float | None = None
    has_video: bool = False
    has_audio: bool = False


@dataclass(frozen=True)
class MediaInfo:
    title: str
    webpage_url: str
    thumbnail: str | None = None
    duration: float | None = None
    uploader: str | None = None
    formats: list[MediaFormat] = field(default_factory=list)
