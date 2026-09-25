"""Basic Telegram commands."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="start")


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer("👋 Bot foundation is running.\n\nSend a supported webpage URL for automatic detection.")


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer("Commands:\n/start — Start the bot\n/help — Show this help\n\nSend a URL directly; it will be detected automatically.")
