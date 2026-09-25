"""Create and configure the Telegram dispatcher."""

from aiogram import Dispatcher
from app.bot.handlers import start, url


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(url.router)
    return dp
