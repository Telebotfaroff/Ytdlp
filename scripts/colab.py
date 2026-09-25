"""Colab launcher for the Telegram bot."""

import asyncio

from dotenv import load_dotenv

from run import main


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
