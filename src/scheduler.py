import logging
import os
import json
from pathlib import Path
from telegram.ext import ContextTypes
from src.news_fetcher import fetch_articles
from src.analyser import analyse_articles
from src.subscribers import load_subscribers

logger = logging.getLogger(__name__)

LAST_ARTICLES_PATH = Path("logs/last_articles.json")


def _save_last_articles(articles):
    LAST_ARTICLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [{"title": a.title, "url": a.url, "source": a.source, "summary": a.summary, "published": a.published} for a in articles]
    LAST_ARTICLES_PATH.write_text(json.dumps(data))


async def schedule_digest(context: ContextTypes.DEFAULT_TYPE):
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("No subscribers, skipping digest.")
        return

    try:
        articles = await fetch_articles()
        digest, top_articles = await analyse_articles(articles)
        _save_last_articles(top_articles)

        for chat_id in subscribers:
            try:
                await _send_long_message(context.bot, chat_id, digest)
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Digest failed: {e}")


async def _send_long_message(bot, chat_id, text: str):
    parts = [p.strip() for p in text.split("———") if p.strip()]
    if len(parts) <= 1:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for part in parts:
        if len(part) > 4000:
            chunks = [part[i:i+4000] for i in range(0, len(part), 4000)]
            for chunk in chunks:
                await bot.send_message(chat_id=chat_id, text=chunk)
        else:
            await bot.send_message(chat_id=chat_id, text=part)
