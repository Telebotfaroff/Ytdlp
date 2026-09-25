"""Project entry point."""

from app.config.settings import settings


if __name__ == "__main__":
    settings.prepare_directories()
    print("Ytdlp bot foundation initialized. Telegram bot startup will be added in Step 2.")
