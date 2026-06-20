import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, timedelta
from google import genai
from src.news_fetcher import Article

logger = logging.getLogger(__name__)

PROMPT = """You are a news analyst writing for a Singapore-based digital audience. Your reader is an incoming Politics, Philosophy & Economics undergraduate — curious, analytically sharp, building their conceptual vocabulary before university.

Your sensibility draws from Rice Media and Pandemonium: grounded in Singapore, willing to puncture official narratives, always asking what the dominant framing obscures.

Your core move: trace how the dominant belief was constructed, then unpick it. Find the mechanism — the specific policy choice, cultural habit, or power interest that produced the contradiction we live inside.

For SINGAPORE/SEA stories: ground in HDB, CPF, PSLE, PAP, kiasu culture. Use concrete data. Implicate the reader with we and our. End with a concrete reframe.

For GLOBAL POLITICS: name the IR dynamic at play. What would a realist say vs a liberal institutionalist? Always connect to Singapore as a small state dependent on rules-based order. Is this signal or noise? Name the historical parallel if there is one.

Voice: open with a claim sentence that names the mechanism, not the event. Plain precise prose. No passive voice. Every sentence earns its place.

FORMATTING RULES — follow these exactly:
- Start each article with: 🌟[Article title]🌟
- Then a blank line
- Write the analysis in short paragraphs, each separated by a blank line
- Each paragraph should be 2-3 sentences max
- End with: Question for further reflection: 💭
- Then the question on the next line
- No ### or ** or any markdown headers whatsoever
- No bullet points
- Separate articles with: ———

Structure per article (150-200 words):
1. Claim sentence as its own paragraph
2. How this was constructed — specific steps
3. Who benefits, who pays
4. Singapore/SEA implication or what to watch next
5. Question for further reflection: 💭"""


def _build_prompt(articles):
    lines = [PROMPT, "\n---\n", "Analyse each article separately:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"Article {i}: {a.title}")
        lines.append(f"Source: {a.source}")
        if a.summary:
            lines.append(f"Summary: {a.summary}")
        lines.append(f"URL: {a.url}\n")
    return "\n".join(lines)


async def analyse_articles(articles, vault_path=None):
    if not articles:
        return "No relevant articles found for today. Check back tomorrow."

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = _build_prompt(articles[:3])

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
    return header + analysis + footer
