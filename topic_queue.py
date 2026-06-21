"""
topic_queue.py
Manages the pre-defined topic queue (topics.json).
Pops the next topic from the queue, marks it as used.
When the queue is exhausted, raises an error so the operator knows to refill it.
"""

import json
import os
import logger

TOPICS_FILE = os.path.join(os.path.dirname(__file__), "topics.json")


def _load() -> dict:
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def next_topic() -> dict:
    """
    Returns the next topic dict from the queue and moves it to 'used'.
    Raises RuntimeError if the queue is empty.
    """
    data = _load()

    if not data["queue"]:
        raise RuntimeError(
            "Topic queue is empty! Add more topics to topics.json → 'queue' list. "
            f"Already used {len(data['used'])} topic(s): "
            + ", ".join(t["topic"] for t in data["used"])
        )

    topic = data["queue"].pop(0)          # take the first item (FIFO)
    data["used"].append(topic)
    _save(data)

    logger.info(f"Topic queue: {len(data['queue'])} remaining, {len(data['used'])} used")
    logger.info(f"Selected topic: {topic['topic']}")
    return topic


def queue_status() -> dict:
    """Returns a summary of queue state without consuming a topic."""
    data = _load()
    return {
        "remaining": len(data["queue"]),
        "used": len(data["used"]),
        "next": data["queue"][0]["topic"] if data["queue"] else None
    }
