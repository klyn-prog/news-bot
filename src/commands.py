import os
import logging
import json
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from src.news_fetcher import fetch_articles
from src.analyser import analyse_articles, explain_article, fun_facts
from src.subscribers import add_subscriber, remove_subscriber, load_subscribers

logger = logging.getLogger(__name__)

LAST_ARTICLES_PATH = Path("logs/last_articles.json")


def _save_last_articles(articles):
    LAST_ARTICLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [{"title": a.title, "url": a.url, "source": a.source, "summary": a.summary, "published": a.published} for a in articles]
    LAST_ARTICLES_PATH.write_text(json.dumps(data))


def _load_last_articles():
    if not LAST_ARTICLES_PATH.exists():
        return []
    from src.news_fetcher import Article
    data = json.loads(LAST_ARTICLES_PATH.read_text())
    return [Article(**d) for d in data]


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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_subscriber(chat_id)
    first_name = update.effective_user.first_name or "there"
    await update.message.reply_text(
        f"hi {first_name}! good morning! ☀️ welcome to klyn's news bot! this bot will send you three stories on geopolitics, sg and sea, and an analysis on them, every morning at 7:30 SGT! hopefully this is a successful get-smarter-quick scheme!\n\n"
        f"here's what you can do:\n\n"
        f"/digest — get today's digest\n"
        f"/explain 1 — background briefing on story 1\n"
        f"/explain 2 — background briefing on story 2\n"
        f"/explain 3 — background briefing on story 3\n"
        f"/funfacts — etymology and history fun facts from today's news\n"
        f"/stop — unsubscribe"
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    remove_subscriber(chat_id)
    first_name = update.effective_user.first_name or "there"
    await update.message.reply_text(f"bye {first_name}! send /start anytime to come back ☀️")


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    first_name = update.effective_user.first_name or "there"
    await update.message.reply_text(f"⏳ fetching and analysing for you {first_name} — give me ~30 seconds...")
    try:
        articles = await fetch_articles()
        if not articles:
            Path("logs/seen_articles.json").write_text("[]")
            articles = await fetch_articles()
        digest, top_articles = await analyse_articles(articles)
        _save_last_articles(top_articles)
        await _send_long_message(context.bot, chat_id, digest)
    except Exception as e:
        logger.error(f"/digest error: {e}")
        await update.message.reply_text(f"❌ something went wrong: {e}")


async def cmd_explain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if not args or args[0] not in ["1", "2", "3"]:
        await update.message.reply_text("please type /explain 1, /explain 2, or /explain 3 to get a background briefing on one of today's stories.")
        return

    index = int(args[0]) - 1
    articles = _load_last_articles()

    if not articles or index >= len(articles):
        await update.message.reply_text("no digest found yet — send /digest first to get today's stories.")
        return

    await update.message.reply_text("📖 pulling together the background briefing — give me a moment...")
    briefing = await explain_article(articles[index])
    await _send_long_message(context.bot, chat_id, briefing)


async def cmd_funfacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    articles = _load_last_articles()
    await update.message.reply_text("🤓 digging up the weird and wonderful — give me a second...")
    result = await fun_facts(articles)
    await _send_long_message(context.bot, chat_id, result)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = load_subscribers()
    await update.message.reply_text(
        f"bot status\n\n🤖 running\n👥 subscribers: {len(subs)}\n🗞 feeds: 14 sources\n⏰ next digest: 07:30 SGT"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)
