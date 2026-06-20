"""
news_fetcher.py
Pulls articles from RSS feeds across geopolitics, SEA, Singapore & social commentary.
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import feedparser
import httpx

logger = logging.getLogger(__name__)

CACHE_PATH = Path("logs/seen_articles.json")

# ── Feed sources ────────────────────────────────────────────────────────────
FEEDS = {
    # Singapore & SEA
    "CNA Singapore":       "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511",
    "CNA Asia":            "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6512",
    "Straits Times":       "https://www.straitstimes.com/news/singapore/rss.xml",
    "TODAY Online":        "https://www.todayonline.com/feed",
    "Coconuts Singapore":  "https://coconuts.co/singapore/feed/",
    "New Naratif":         "https://newnaratif.com/feed/",

    # Global geopolitics
    "Al Jazeera":          "https://www.aljazeera.com/xml/rss/all.xml",
    "Foreign Policy":      "https://foreignpolicy.com/feed/",
    "The Diplomat":        "https://thediplomat.com/feed/",
    "Rest of World":       "https://restofworld.org/feed/",
    "Guardian World":      "https://www.theguardian.com/world/rss",

    # Social commentary
    "Aeon Magazine":       "https://aeon.co/feed.rss",
    "Noema Magazine":      "https://www.noemamag.com/feed/",
    "Delayed Gratification": "https://www.slow-journalism.com/feed",
}

# ── Keywords for filtering ──────────────────────────────────────────────────
RELEVANT_KEYWORDS = [
    # SEA / Singapore
    "singapore", "malaysia", "indonesia", "thailand", "myanmar", "asean",
    "southeast asia", "sea", "mekong", "hdb", "cpf", "pap", "mrt",

    # Geopolitics
    "geopolitic", "conflict", "war", "sanction", "diplomacy", "treaty",
    "nato", "china", "united states", "russia", "taiwan", "south china sea",
    "middle east", "ukraine", "israel", "gaza", "iran", "north korea",
    "election", "coup", "protest", "referendum",

    # Social
    "inequality", "class", "race", "gender", "identity", "climate",
    "migration", "refugee", "housing", "cost of living", "mental health",
    "social media", "surveillance", "censorship", "free speech",
    "marginalised", "minority", "queer", "lgbtq",
]

BORING_KEYWORDS = [
    "recipe", "celebrity", "fashion", "beauty", "sports score",
    "box office", "tv show", "movie review", "horoscope",
]


@dataclass
class Article:
    title: str
    url: str
    source: str
    summary: str
    published: str
    relevance_score: int = 0

    def uid(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()


def _load_seen() -> set:
    if CACHE_PATH.exists():
        return set(json.loads(CACHE_PATH.read_text()))
    return set()


def _save_seen(seen: set):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(list(seen)))


def _score_article(article: Article) -> int:
    text = (article.title + " " + article.summary).lower()
    score = 0
    for kw in RELEVANT_KEYWORDS:
        if kw in text:
            score += 1
    for kw in BORING_KEYWORDS:
        if kw in text:
            score -= 3
    return score


def _is_recent(entry) -> bool:
    """Only include articles published in the last 24 hours."""
    try:
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - published < timedelta(hours=24)
    except Exception:
        return True  # include if date is missing


async def fetch_articles(max_per_feed: int = 10) -> list[Article]:
    seen = _load_seen()
    articles: list[Article] = []

    async with httpx.AsyncClient(timeout=15) as client:
        tasks = [_fetch_feed(client, name, url, max_per_feed) for name, url in FEEDS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Feed fetch error: {result}")
            continue
        for article in result:
            if article.uid() in seen:
                continue
            article.relevance_score = _score_article(article)
            if article.relevance_score > 0:
                articles.append(article)

    # Mark all fetched as seen
    new_seen = seen | {a.uid() for a in articles}
    _save_seen(new_seen)

    # Sort by relevance, return top 20 for analysis
    articles.sort(key=lambda a: a.relevance_score, reverse=True)
    return articles[:20]


async def _fetch_feed(client: httpx.AsyncClient, name: str, url: str, max_per_feed: int) -> list[Article]:
    try:
        resp = await client.get(url, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:max_per_feed]:
            if not _is_recent(entry):
                continue
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            # Strip HTML tags crudely
            import re
            summary = re.sub(r"<[^>]+>", "", summary)[:400]
            articles.append(Article(
                title=entry.get("title", "No title").strip(),
                url=entry.get("link", ""),
                source=name,
                summary=summary.strip(),
                published=entry.get("published", ""),
            ))
        return articles
    except Exception as e:
        logger.warning(f"[{name}] Error: {e}")
        return []
