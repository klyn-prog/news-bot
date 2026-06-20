# 🌅 Morning Digest Bot

A personal Telegram bot that fetches news across **geopolitics, Singapore & SEA, and social commentary** — then analyses each article in a voice modelled on Rice Media: grounded, humanising, and willing to ask the uncomfortable question.

Delivers a daily digest at **07:30 SGT** and can also be triggered on demand.

---

## What it does

1. **Pulls RSS feeds** from ~14 sources (CNA, Straits Times, Al Jazeera, Foreign Policy, The Diplomat, Guardian, Aeon, New Naratif, Rest of World, and more)
2. **Filters** articles by relevance using keyword scoring — skips entertainment, celebrity, and press releases
3. **Deduplicates** so you never see the same article twice across days
4. **Analyses** the top stories using Claude (Anthropic API) in Rice Media's voice: plain prose, humanising, power-aware, SEA-grounded
5. **Personalises** analysis using your Obsidian vault — the bot reads your recent notes to understand what you care about and adjusts depth accordingly
6. **Sends to Telegram** as a formatted morning digest, split into readable mobile chunks

---

## Setup (15 minutes)

### 1. Prerequisites
- Python 3.11+
- A Telegram account
- Anthropic API key ([get one here](https://console.anthropic.com))

### 2. Create your Telegram bot

1. Open Telegram → search for **@BotFather**
2. Send `/newbot`, follow the prompts
3. Copy the **bot token** (looks like `1234567890:ABCdef...`)
4. Find your **chat ID**: message [@userinfobot](https://t.me/userinfobot) → it shows your ID

### 3. Install dependencies

```bash
cd news-bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

Fill in:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=987654321
ANTHROPIC_API_KEY=sk-ant-...
OBSIDIAN_VAULT_PATH=/Users/yourname/Documents/MyVault   # optional
```

### 5. Run the bot

```bash
python bot.py
```

The bot will start and schedule the digest for 07:30 SGT each day. Send `/digest` in Telegram to get one immediately.

---

## Obsidian Integration

The bot reads your Obsidian vault to build a **reading preference profile** — it looks at your 30 most recently modified notes, extracts titles and opening lines, and uses these to:

- Prioritise stories that connect to themes you've been thinking about
- Adjust the depth and angle of analysis accordingly
- Surface connections to things in your notes (without explicitly quoting them)

**How to set it up:**

1. Find your Obsidian vault folder path:
   - macOS: Usually `~/Documents/YourVaultName` or `~/ObsidianVault`
   - Windows: `C:\Users\yourname\Documents\YourVaultName`
2. Add the full path to `.env` as `OBSIDIAN_VAULT_PATH`
3. Restart the bot

**Syncing notes across devices:**
- **Obsidian Sync** (paid): Notes sync automatically; point to the local synced folder
- **iCloud** (macOS/iOS): Vault lives in `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/VaultName`
- **Git**: Clone your vault repo locally, point to that folder
- **Dropbox/OneDrive**: Point to the synced local folder

The bot only *reads* your notes — it never writes to your vault.

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Introduction and command list |
| `/digest` | Trigger digest immediately |
| `/status` | Check bot health and config |
| `/help` | Show help |

---

## Customising feeds and topics

Edit `src/news_fetcher.py`:

**Add/remove RSS feeds** — find the `FEEDS` dict near the top. Any RSS/Atom feed URL works.

**Adjust keyword filtering** — edit `RELEVANT_KEYWORDS` to add topics you care about, or `BORING_KEYWORDS` to suppress more noise.

**Change digest time** — edit `bot.py`, the `time(23, 30)` is UTC. SGT is UTC+8, so SGT 07:30 = UTC 23:30 (previous calendar day).

**Adjust analysis depth/style** — edit the `RICE_MEDIA_SYSTEM_PROMPT` in `src/analyser.py`.

---

## Running permanently (optional)

To keep the bot running after you close your terminal, use `screen`, `tmux`, or set up a system service.

**Simple option with screen:**
```bash
screen -S newsbot
python bot.py
# Detach: Ctrl+A then D
# Reattach: screen -r newsbot
```

**Or run on a free server**: Railway.app, Fly.io, and Render all have free tiers that can host a lightweight Python bot.

---

## File structure

```
news-bot/
├── bot.py                  # Entry point, scheduler setup
├── requirements.txt
├── .env.example            # Config template
├── src/
│   ├── news_fetcher.py     # RSS fetching + keyword filtering
│   ├── analyser.py         # Claude API + Obsidian context
│   ├── scheduler.py        # Daily digest job
│   └── commands.py         # Telegram command handlers
└── logs/
    ├── bot.log             # Runtime logs
    └── seen_articles.json  # Dedup cache
```
