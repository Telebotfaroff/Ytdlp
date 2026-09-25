"""Project entry point."""

import asyncio
import logging
import os

from aiogram import Bot
from dotenv import load_dotenv
from pyrogram import Client

from app.bot.dispatcher import create_dispatcher
from app.config.settings import settings
from app.media.cleanup import cleanup_runtime_storage
from app.upload.telegram import TelegramUploader, set_telegram_uploader


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )


async def main() -> None:
    load_dotenv()
    configure_logging()
    logger = logging.getLogger("ytdlp")
    settings.prepare_directories()
    logger.info("Starting Ytdlp Telegram Bot")

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured.")
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required for Pyrogram.")

    logger.info("Download directory: %s", settings.download_dir.resolve())
    logger.info("Temp directory: %s", settings.temp_dir.resolve())

    pyrogram_client = Client(
        "yt_dlp_bot",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.bot_token,
        workdir=str(settings.temp_dir),
    )

    logger.info("Starting Pyrogram...")
    await pyrogram_client.start()
    logger.info("Pyrogram started.")
    set_telegram_uploader(TelegramUploader(pyrogram_client))

    bot = Bot(token=settings.bot_token)
    dispatcher = create_dispatcher()
    cleanup_task = asyncio.create_task(_cleanup_loop())

    try:
        logger.info("Starting aiogram polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        logger.info("Stopping bot...")
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        await bot.session.close()
        await pyrogram_client.stop()


async def _cleanup_loop() -> None:
    logger = logging.getLogger("ytdlp.cleanup")
    while True:
        try:
            cleanup_runtime_storage(
                settings.download_dir,
                settings.temp_dir,
                settings.media_session_ttl_seconds,
            )
        except Exception:
            logger.exception("Cleanup failed")
        await asyncio.sleep(900)


if __name__ == "__main__":
    asyncio.run(main())
