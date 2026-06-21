"""
topics.py
Manages topics.json — a queue of unused topics and a log of used ones.

Shared by Mode 0 (history narration) and Mode 2 (Did You Know).
Each call to next_topic() pops the first item from "queue" and
moves it to "used", so the same topic is never repeated until
all topics are exhausted — at which point the used list is
recycled back into the queue (shuffled).

topics.json shape:
{
  "queue": [ { "topic": "...", "hint": "..." }, ... ],
  "used":  [ { "topic": "...", "hint": "..." }, ... ]
}
"""

import json
import os
import random
import logger

TOPICS_PATH = os.path.join(os.path.dirname(__file__), "topics.json")


def _load() -> dict:
    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    with open(TOPICS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def next_topic() -> dict:
    """
    Pop the next topic from the queue and mark it used.
    Returns { "topic": str, "hint": str }.

    If the queue is empty, recycles all used topics back into
    the queue (shuffled) and starts over.
    """
    data = _load()

    if not data["queue"]:
        logger.warning("All topics used — recycling used list back into queue (shuffled).")
        recycled = data["used"][:]
        random.shuffle(recycled)
        data["queue"] = recycled
        data["used"] = []
        _save(data)

    topic = data["queue"].pop(0)
    data["used"].append(topic)
    _save(data)

    logger.info(f"Topic selected: {topic['topic']}")
    return topic


def peek_queue_size() -> int:
    """Return how many topics remain in the queue (informational)."""
    return len(_load()["queue"])


def mark_failed(topic: dict):
    """
    If script generation fails completely for a topic, push it to the
    end of the queue instead of losing it, and remove it from used.
    """
    data = _load()
    # Remove from used if it got added
    data["used"] = [t for t in data["used"] if t["topic"] != topic["topic"]]
    # Push to end of queue so it gets retried later
    data["queue"].append(topic)
    _save(data)
    logger.warning(f"Topic '{topic['topic']}' returned to end of queue.")
