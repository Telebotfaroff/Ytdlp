"""Project entry point."""

import asyncio

from aiogram import Bot
from dotenv import load_dotenv

from app.bot.dispatcher import create_dispatcher
from app.config.settings import settings


async def main() -> None:
    load_dotenv()
    settings.prepare_directories()

    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured. Set it in the environment or .env file.")

    bot = Bot(token=settings.bot_token)
    dispatcher = create_dispatcher()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
