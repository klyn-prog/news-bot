"""
subscribers.py
Manages a simple list of subscriber chat IDs saved to disk.
"""

import json
from pathlib import Path

SUBSCRIBERS_PATH = Path("logs/subscribers.json")


def load_subscribers() -> set:
    if SUBSCRIBERS_PATH.exists():
        return set(json.loads(SUBSCRIBERS_PATH.read_text()))
    return set()


def save_subscribers(subscribers: set):
    SUBSCRIBERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBSCRIBERS_PATH.write_text(json.dumps(list(subscribers)))


def add_subscriber(chat_id: int):
    subs = load_subscribers()
    subs.add(chat_id)
    save_subscribers(subs)


def remove_subscriber(chat_id: int):
    subs = load_subscribers()
    subs.discard(chat_id)
    save_subscribers(subs)
