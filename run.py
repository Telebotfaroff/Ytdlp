"""Project entry point."""

import asyncio

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from dotenv import load_dotenv

from app.bot.dispatcher import create_dispatcher
from app.media.cleanup import cleanup_runtime_storage
from app.config.settings import settings


async def main() -> None:
    load_dotenv()
    settings.prepare_directories()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured. Set it in the environment or .env file.")

    api = TelegramAPIServer.from_base(
        settings.telegram_api_base,
        is_local=settings.telegram_api_is_local,
    )
    session = AiohttpSession(api=api)
    bot = Bot(token=settings.bot_token, session=session)
    dispatcher = create_dispatcher()
    cleanup_task = asyncio.create_task(_cleanup_loop())

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        await bot.session.close()


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
