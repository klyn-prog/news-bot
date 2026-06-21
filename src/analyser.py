import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, timedelta
from google import genai
from src.news_fetcher import Article

logger = logging.getLogger(__name__)

DIGEST_PROMPT = """You are a news analyst writing for a Singapore-based digital audience. Your reader is an incoming Politics, Philosophy & Economics undergraduate.

Your core move: trace how the dominant belief was constructed, then unpick it. Find the mechanism.

For SINGAPORE/SEA: ground in HDB, CPF, PSLE, PAP, kiasu culture. Use data. Implicate the reader.
For GLOBAL POLITICS: name the IR dynamic. Connect to Singapore as a small state. Signal or noise? Historical parallel?

FORMATTING — follow exactly:
- Start with: 🌟[Article title]🌟
- Blank line
- 📰 What happened:
- 2-3 short fact paragraphs (who, what, when, where — no analysis)
- Blank line
- 🔍 Analysis:
- 2-3 short analytical paragraphs. Open with a claim sentence naming the mechanism. Trace construction. Follow the power. Connect to Singapore/SEA.
- Blank line
- 📚 [One theory name from politics, philosophy or economics]:
- 2-3 sentences explaining the theory clearly and how it applies here. Write for someone who has never heard of it.
- Blank line
- 💭 Question for further reflection:
- The question on the next line
- Blank line
- 🔗 Read more: [article URL]
- 📖 Type /explain [article number] for a deeper background briefing on this story
- Separate articles with: ———

NO ### or ** or markdown headers. NO bullet points. Short paragraphs only."""

EXPLAIN_PROMPT = """You are a news analyst and educator. Write a thorough but accessible background briefing.

Cover:
1. 🌍 Background and History: How did this situation develop? Key historical moments.
2. 👥 Key Players: Main actors, their interests and motivations.
3. ⚙️ How it works: Explain any systems or institutions the reader needs to understand.
4. 🇸🇬 Why Singapore should care: Trade, diplomacy, economics, historical ties.
5. 📚 Key concepts: 2-3 academic concepts from PPE that help make sense of this. Explain each in 2-3 sentences as if the reader has never encountered them.

Plain clear prose. No jargon without explanation. Short paragraphs. 400-500 words."""

FUNFACTS_PROMPT = """You are an enthusiastic etymology nerd and history obsessive — think the energy of @etymologynerd on social media. You find the weird, delightful, and surprising hidden inside everyday words and historical moments.

Given today's news stories, generate 3 fun facts — one connected to each story. Each fact should be:
- About etymology (word origins), bizarre historical footnotes, linguistic quirks, or surprising cultural connections
- Genuinely surprising — the kind of thing that makes you go "wait, really?!"
- Short and punchy — 3-4 sentences max
- Connected to a specific word, place name, concept, or person mentioned in the story

FORMATTING:
- Start with: 🤓 Fun Facts of the Day
- Blank line
- For each fact:
  - 💡 [A snappy title for the fact]
  - The fact in 3-4 sentences
  - Blank line
- End with: _connected to today's stories — type /digest to read them_

NO ### or ** or markdown headers. Keep it fun and conversational."""


def _build_digest_prompt(articles):
    lines = [DIGEST_PROMPT, "\n---\n", "Analyse each article separately:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"Article {i}: {a.title}")
        lines.append(f"Source: {a.source}")
        if a.summary:
            lines.append(f"Summary: {a.summary}")
        lines.append(f"URL: {a.url}\n")
    return "\n".join(lines)


def _build_explain_prompt(article):
    return f"""{EXPLAIN_PROMPT}

Article to brief on:
Title: {article.title}
Source: {article.source}
Summary: {article.summary}
URL: {article.url}"""


def _build_funfacts_prompt(articles):
    lines = [FUNFACTS_PROMPT, "\n---\n", "Today's stories:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"Story {i}: {a.title}")
        if a.summary:
            lines.append(f"Summary: {a.summary}\n")
    return "\n".join(lines)


async def analyse_articles(articles, vault_path=None):
    if not articles:
        return "No relevant articles found for today. Check back tomorrow.", []

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = _build_digest_prompt(articles[:3])

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        analysis = response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        analysis = f"[Analysis unavailable today: {e}]"

    sgt = timezone(timedelta(hours=8))
    date_str = datetime.now(sgt).strftime("%A, %d %B %Y")
    header = f"🌅 Morning Digest — {date_str}\nTop 3 stories worth your attention\n\n"
    footer = "\n\n— Your 07:30 SGT digest"
    return header + analysis + footer, articles[:3]


async def explain_article(article):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = _build_explain_prompt(article)

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return f"📖 Background Briefing: {article.title}\n\n{response.text}\n\n🔗 {article.url}"
    except Exception as e:
        logger.error(f"Gemini explain error: {e}")
        return f"[Briefing unavailable: {e}]"


async def fun_facts(articles):
    if not articles:
        return "no digest yet — send /digest first to get today's stories, then try /funfacts!"

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = _build_funfacts_prompt(articles)

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini funfacts error: {e}")
        return f"[Fun facts unavailable today: {e}]"
