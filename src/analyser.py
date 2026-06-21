import logging
import os
from pathlib import Path
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

NO ### or ** or markdown headers. NO bullet points. NO numbered lists. Short paragraphs only."""

EXPLAIN_PROMPT = """You are a news analyst and educator. Write a thorough but accessible background briefing for a Telegram message.

STRICT FORMATTING RULES:
- NO bullet points
- NO numbered lists
- NO ** bold ** or markdown
- Short paragraphs only (2-3 sentences)
- Use these exact emoji headers for each section, each on its own line

Structure:
🌍 Background & History
[2-3 short paragraphs on how this situation developed and key historical moments]

👥 Key Players
[2-3 short paragraphs naming the main actors, their interests and motivations]

⚙️ How It Works
[2-3 short paragraphs explaining any systems or institutions the reader needs to understand]

🇸🇬 Why Singapore Should Care
[2-3 short paragraphs connecting to Singapore — trade, diplomacy, economics, historical ties]

📚 Key Concepts
[3 concepts from politics, philosophy or economics. For each: write the concept name followed by a colon, then 2-3 sentences explaining it plainly. Separate each with a blank line.]

Total: 400-500 words. Plain conversational prose. No jargon without explanation."""

FUNFACTS_PROMPT = """You are an enthusiastic etymology nerd and history obsessive. You find the weird, delightful, and surprising hidden inside everyday words and historical moments.

Given today's news stories, generate 3 fun facts — one connected to each story. Each fact should be about etymology, bizarre historical footnotes, linguistic quirks, or surprising cultural connections. Genuinely surprising. Short and punchy — 3-4 sentences max.

FORMATTING:
- Start with: 🤓 Fun Facts of the Day
- Blank line
- For each fact:
  - 💡 [A snappy title for the fact]
  - The fact in 3-4 sentences
  - Blank line
- End with: type /digest to read today's stories

NO ### or ** or markdown. NO bullet points."""

VOCABULARY_PROMPT = """You are a PPE tutor helping an undergraduate build their academic vocabulary.

From the news articles provided, pick 3 important academic or political terms that appear or are relevant. For each term explain it clearly for someone who has never studied PPE.

FORMATTING — follow exactly:
- Start with: 📖 Vocabulary of the Day
- Blank line
- For each term:
  - 🔤 [Term]
  - Definition: 2-3 sentences explaining what it means in plain English
  - In context: 1-2 sentences connecting it to today's story
  - Blank line
- End with: these terms will come up a lot in your PPE degree — worth remembering!

NO ### or ** or markdown. NO bullet points. NO numbered lists."""

DEBATE_PROMPT = """You are a debate coach preparing an undergraduate for a PPE seminar. Based on the main issue in today's top news story, write a structured debate brief.

FORMATTING — follow exactly:
- Start with: ⚖️ Today's Debate
- Blank line
- The issue: [one sentence stating the debate motion clearly]
- Blank line
- 👍 The case FOR:
- 3 short paragraphs, each making one strong argument. Each paragraph is 2-3 sentences. No bullet points.
- Blank line
- 👎 The case AGAINST:
- 3 short paragraphs, each making one strong argument. Each paragraph is 2-3 sentences. No bullet points.
- Blank line
- 🎯 The crux:
- 1-2 sentences identifying the single most important point of disagreement between the two sides
- Blank line
- 💭 Which side do you find more convincing, and why?

NO ### or ** or markdown. NO bullet points. Plain prose only."""

CONNECTIONS_PROMPT = """You are a lateral thinking analyst who finds surprising hidden connections between seemingly unrelated news stories.

Given today's 3 news stories, find the single most surprising and intellectually interesting connection between them. It could be a shared structural pattern, a historical parallel, a common underlying cause, or a philosophical thread that ties them together.

FORMATTING — follow exactly:
- Start with: 🕸️ The Hidden Connection
- Blank line
- Write 3-4 paragraphs exploring the connection. Be specific and surprising — not vague ("they're all about power"). Go deep.
- Blank line
- 💭 What this suggests:
- 1-2 sentences on what this connection reveals about the world right now
- Blank line
- Today's stories: [list the 3 titles briefly]

NO ### or ** or markdown. NO bullet points. Short paragraphs only."""

TIMELINE_PROMPT = """You are a historian and political analyst. The user has asked for a timeline of a specific topic.

Using your knowledge and any available information, create a clear and engaging historical timeline.

FORMATTING — follow exactly:
- Start with: 📅 Timeline: [Topic]
- Blank line
- For each entry:
  - 🗓 [Year or period]: [What happened — 2-3 sentences explaining significance, not just facts]
  - Blank line
- Include 8-10 key moments, from origins to present day
- End with: 🔮 What to watch: [1-2 sentences on what comes next]
- Then: 🇸🇬 Singapore angle: [1-2 sentences on how this connects to Singapore]

NO ### or ** or markdown. NO bullet points. Short paragraphs only. Make it feel like a story, not a list."""

THISWEEK_PROMPT = """You are a historian. The user wants to know what was happening in world history exactly this week in a specific year.

Find 4-5 significant events that occurred during this week in that year. Prioritise events with lasting historical significance — political, social, economic, or cultural.

FORMATTING — follow exactly:
- Start with: 🗓 This Week in [year]
- Blank line
- For each event:
  - 📌 [Exact date if known]: [Event name]
  - 2-3 sentences explaining what happened and why it mattered historically
  - Blank line
- End with: 🔗 The thread: [1-2 sentences finding a common theme across this week's events]
- Then: 🇸🇬 Singapore then: [1-2 sentences on what was happening in Singapore or SEA that year]

NO ### or ** or markdown. NO bullet points. Make history feel alive."""


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


def _build_vocabulary_prompt(articles):
    lines = [VOCABULARY_PROMPT, "\n---\n", "Today's stories:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"Story {i}: {a.title}")
        if a.summary:
            lines.append(f"Summary: {a.summary}\n")
    return "\n".join(lines)


def _build_debate_prompt(article):
    return f"""{DEBATE_PROMPT}

Today's top story:
Title: {article.title}
Source: {article.source}
Summary: {article.summary}"""


def _build_connections_prompt(articles):
    lines = [CONNECTIONS_PROMPT, "\n---\n", "Today's 3 stories:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"Story {i}: {a.title}")
        if a.summary:
            lines.append(f"Summary: {a.summary}\n")
    return "\n".join(lines)


def _get_client():
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


async def analyse_articles(articles, vault_path=None):
    if not articles:
        return "No relevant articles found for today. Check back tomorrow.", []

    client = _get_client()
    prompt = _build_digest_prompt(articles[:3])

    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
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
    client = _get_client()
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=_build_explain_prompt(article))
        return f"📖 Background Briefing: {article.title}\n\n{response.text}\n\n🔗 {article.url}"
    except Exception as e:
        logger.error(f"Gemini explain error: {e}")
        return f"[Briefing unavailable: {e}]"


async def fun_facts(articles):
    if not articles:
        return "no digest yet — send /digest first!"
    client = _get_client()
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=_build_funfacts_prompt(articles))
        return response.text
    except Exception as e:
        return f"[Fun facts unavailable: {e}]"


async def vocabulary(articles):
    if not articles:
        return "no digest yet — send /digest first!"
    client = _get_client()
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=_build_vocabulary_prompt(articles))
        return response.text
    except Exception as e:
        return f"[Vocabulary unavailable: {e}]"


async def debate(articles):
    if not articles:
        return "no digest yet — send /digest first!"
    client = _get_client()
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=_build_debate_prompt(articles[0]))
        return response.text
    except Exception as e:
        return f"[Debate unavailable: {e}]"


async def connections(articles):
    if not articles:
        return "no digest yet — send /digest first!"
    client = _get_client()
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=_build_connections_prompt(articles))
        return response.text
    except Exception as e:
        return f"[Connections unavailable: {e}]"


async def timeline(topic: str):
    client = _get_client()
    prompt = TIMELINE_PROMPT + f"\n\nTopic to cover: {topic}"
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"tools": [{"google_search": {}}]}
        )
        return response.text
    except Exception as e:
        # fallback without search
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return response.text
        except Exception as e2:
            return f"[Timeline unavailable: {e2}]"


async def thisweek(year: str):
    client = _get_client()
    sgt = timezone(timedelta(hours=8))
    now = datetime.now(sgt)
    week_str = now.strftime("the week of %B %-d")
    prompt = THISWEEK_PROMPT + f"\n\nYear requested: {year}\nCurrent week: {week_str}"
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"tools": [{"google_search": {}}]}
        )
        return response.text
    except Exception as e:
        try:
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return response.text
        except Exception as e2:
            return f"[This week unavailable: {e2}]"
