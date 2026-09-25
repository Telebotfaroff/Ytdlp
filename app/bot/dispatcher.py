"""Create and configure the Telegram dispatcher."""

from aiogram import Dispatcher

from app.bot.callbacks import router as callback_router
from app.bot.handlers import start, url


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(url.router)
    dp.include_router(callback_router)
    return dp
