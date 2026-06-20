"""
scheduler.py
Sends the daily digest to all subscribers.
"""

import logging
import os

from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.news_fetcher import fetch_articles
from src.analyser import analyse_articles
from src.subscribers import load_subscribers

logger = logging.getLogger(__name__)


async def schedule_digest(context: ContextTypes.DEFAULT_TYPE):
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("No subscribers, skipping digest.")
        return

    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")

    try:
        articles = await fetch_articles()
        digest = await analyse_articles(articles, vault_path=vault_path)

        for chat_id in subscribers:
            try:
                await _send_long_message(context.bot, chat_id, digest)
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")

    except Exception as e:
        logger.error(f"Digest failed: {e}")


async def _send_long_message(bot, chat_id, text: str):
    limit = 4000
    if len(text) <= limit:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
        return

    parts = text.split("\n---\n")
    current = ""
    for part in parts:
        if len(current) + len(part) + 5 > limit:
            if current:
                await bot.send_message(chat_id=chat_id, text=current, parse_mode=ParseMode.MARKDOWN)
            current = part
        else:
            current += ("\n---\n" if current else "") + part
    if current:
        await bot.send_message(chat_id=chat_id, text=current, parse_mode=ParseMode.MARKDOWN)
