"""Basic Telegram commands."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="start")


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer(
        "👋 Ytdlp bot is running.\n\n"
        "Send a supported webpage URL for automatic detection.\n"
        "Use /help to see available commands."
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(
        "📚 Commands\n\n"
        "/start — Start the bot\n"
        "/help — Show this help\n"
        "/ep <query> — Search using the E API\n"
        "/ph <query> — Search using the PH API\n"
        "/missav <query> — Search using the M API\n"
        "/xh <query> — Search using the XH API\n\n"
        "⬇️ Download:\n"
        "Send a supported URL directly and choose a quality.\n"
        "Custom filename is optional."
    )
