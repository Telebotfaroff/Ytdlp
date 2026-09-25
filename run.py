"""Project entry point."""

import asyncio

from aiogram import Bot
from dotenv import load_dotenv
from pyrogram import Client

from app.bot.dispatcher import create_dispatcher
from app.config.settings import settings
from app.media.cleanup import cleanup_runtime_storage
from app.upload.telegram import TelegramUploader, set_telegram_uploader


async def main() -> None:
    load_dotenv()
    settings.prepare_directories()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured.")
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required for Pyrogram.")

    pyrogram_client = Client(
        "yt_dlp_bot",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.bot_token,
        workdir=str(settings.temp_dir),
    )

    await pyrogram_client.start()
    set_telegram_uploader(TelegramUploader(pyrogram_client))

    bot = Bot(token=settings.bot_token)
    dispatcher = create_dispatcher()
    cleanup_task = asyncio.create_task(_cleanup_loop())

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        await bot.session.close()
        await pyrogram_client.stop()


async def _cleanup_loop() -> None:
    while True:
        cleanup_runtime_storage(
            settings.download_dir,
            settings.temp_dir,
            settings.media_session_ttl_seconds,
        )
        await asyncio.sleep(900)


if __name__ == "__main__":
    asyncio.run(main())
