#!/usr/bin/env python3
"""
Morning Digest Telegram Bot — multi-user version
Anyone who /start's the bot gets added to the daily digest.
"""

import asyncio
import logging
import os
from datetime import time

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.scheduler import schedule_digest
from src.commands import cmd_start, cmd_stop, cmd_digest, cmd_status, cmd_help

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))

    # Daily digest at 7:30 AM Singapore time (UTC 23:30 prev day)
    app.job_queue.run_daily(
        schedule_digest,
        time=time(23, 30),
        name="morning_digest",
    )

    logger.info("Bot started. Digest scheduled at 07:30 SGT daily.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
