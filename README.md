# Ytdlp Telegram Bot

Python-based modular Telegram media bot.

[![Open in Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Telebotfaroff/Ytdlp/blob/main/Ytdlp_Colab.ipynb)
[![Open in Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://www.kaggle.com/notebooks/welcome?src=https://github.com/Telebotfaroff/Ytdlp/blob/main/Ytdlp_Kaggle.ipynb)

## Telegram upload architecture

The bot uses **aiogram** for Bot API updates and UI, and **Pyrogram + MTProto** for Telegram file uploads.

This avoids the cloud Bot API's 50 MB multipart upload limit for the download/upload path and supports large uploads up to Telegram's bot file-size ceiling (2 GB).

Required Telegram credentials:

- `BOT_TOKEN`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

Keep `TELEGRAM_API_HASH` secret.

## Run in Google Colab or Kaggle

Use either launch button above. The notebooks install the project dependencies, FFmpeg, and aria2c, then securely ask for your Telegram credentials before starting the bot.

## Environment

Copy `.env.example` to `.env` and configure the credentials. In Colab/Kaggle, use environment variables or their secret-management features instead of committing credentials.

## Development approach

The project is being built incrementally. Each subsystem is changed and verified before the next one is added.
