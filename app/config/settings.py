"""Environment-based application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    telegram_api_id: int = _env_int("TELEGRAM_API_ID", 0)
    telegram_api_hash: str = os.getenv("TELEGRAM_API_HASH", "")
    download_dir: Path = Path(os.getenv("DOWNLOAD_DIR", "./downloads"))
    temp_dir: Path = Path(os.getenv("TEMP_DIR", "./tmp"))
    max_telegram_file_size: int = _env_int("MAX_TELEGRAM_FILE_SIZE", 2 * 1024**3)
    aria2_connections: int = _env_int("ARIA2_CONNECTIONS", 16)
    aria2_split: int = _env_int("ARIA2_SPLIT", 16)
    aria2_max_concurrent: int = _env_int("ARIA2_MAX_CONCURRENT", 2)
    media_session_ttl_seconds: int = _env_int("MEDIA_SESSION_TTL_SECONDS", 3600)

    def prepare_directories(self) -> None:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
