"""
reddit_story.py
Mode 1 — Fetches a top Reddit story from r/TIFU, r/AmItheAsshole, or r/confessions
and trims it to a Short-friendly script. Uses PRAW (free, no OAuth needed for read).

Install: pip install praw
No API key needed for read-only access with a public client_id.

Setup (one-time):
  1. Go to https://www.reddit.com/prefs/apps
  2. Click "create another app" → choose "script"
  3. Set redirect URI to http://localhost:8080
  4. Copy client_id (under app name) and client_secret
  5. Add to .env:
       REDDIT_CLIENT_ID=your_id
       REDDIT_CLIENT_SECRET=your_secret
"""

import os
import random
import logger
from dotenv import load_dotenv
from config import get, mode_config
from llm_client import chat

load_dotenv()

REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME      = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD      = os.getenv("REDDIT_PASSWORD")


def _fetch_raw_story(subreddit: str, min_score: int) -> dict:
    """Fetch a random top post from the subreddit using PRAW."""
    try:
        import praw
    except ImportError:
        raise ImportError("praw not installed. Run: pip install praw")

    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        raise ValueError(
            "Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET in .env\n"
            "See reddit_story.py header for setup instructions."
        )

    if not REDDIT_USERNAME or not REDDIT_PASSWORD:
        raise ValueError(
            "Missing REDDIT_USERNAME or REDDIT_PASSWORD in .env\n"
            "These are your Reddit account credentials — needed for the script app flow."
        )

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
        user_agent=f"shorts_cash_cow/1.0 by u/{REDDIT_USERNAME}"
    )

    sub = reddit.subreddit(subreddit)
    posts = [
        p for p in sub.top(time_filter="week", limit=50)
        if not p.stickied and p.score >= min_score and len(p.selftext) > 200
    ]

    if not posts:
        raise RuntimeError(f"No suitable posts found in r/{subreddit} (score >= {min_score})")

    post = random.choice(posts[:20])  # pick from top 20 to add variety
    logger.info(f"Selected post: '{post.title}' (score: {post.score}, r/{subreddit})")

    return {
        "title": post.title,
        "body": post.selftext,
        "subreddit": subreddit,
        "score": post.score,
        "url": f"https://reddit.com{post.permalink}"
    }


def _trim_with_llm(raw: dict, max_words: int, min_words: int, cta: str) -> dict:
    """Use the LLM client to condense/rewrite the Reddit post into a punchy Short script."""
    cfg = get()["groq"]

    prompt = f"""
You are a YouTube Shorts scriptwriter. Below is a Reddit post from r/{raw['subreddit']}.
Rewrite it as a gripping, first-person narrated Short script.

Rules:
- Keep the story authentic and personal ("I", "my", etc.)
- Start with a hook that grabs attention instantly (e.g. "So I completely destroyed my relationship in one text...")
- Short, punchy sentences. Build tension. Add a satisfying ending or twist.
- End with: "{cta}"
- Plain text only — no asterisks, headers, stage directions, or emojis
- YOU MUST write between {min_words} and {max_words} words. Count carefully.

Original Reddit post:
TITLE: {raw['title']}
BODY:
{raw['body'][:2000]}

Also provide:
TITLE: (catchy YouTube Shorts title, max 60 chars)
DESCRIPTION: (2-3 sentences with #Shorts #Reddit)
TAGS: (10 comma-separated tags)

Format exactly like this:
SCRIPT:
<script here>

TITLE:
<title here>

DESCRIPTION:
<description here>

TAGS:
<tags here>
"""

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg["temperature"],
    )
    raw_text = response.choices[0].message.content or ""

    def extract(label):
        try:
            start = raw_text.index(f"{label}:") + len(f"{label}:")
            next_labels = ["TITLE:", "DESCRIPTION:", "TAGS:"]
            end = len(raw_text)
            for lbl in next_labels:
                if lbl in raw_text and raw_text.index(lbl) > raw_text.index(f"{label}:"):
                    pos = raw_text.index(lbl)
                    if pos < end:
                        end = pos
            return raw_text[start:end].strip()
        except ValueError:
            return ""

    return {
        "script": extract("SCRIPT"),
        "title": extract("TITLE"),
        "description": extract("DESCRIPTION"),
        "tags": [t.strip() for t in extract("TAGS").split(",")],
        "keywords": [],          # not needed — gameplay video used as background
        "source_url": raw["url"]
    }


def generate_reddit_script() -> dict:
    """Main entry point for Mode 1. Returns same shape as generate_script()."""
    cfg = mode_config()
    subreddits = cfg["subreddits"]
    min_score = cfg["min_score"]
    max_words = cfg["max_words"]
    min_words = cfg["min_words"]
    cta = cfg["cta"]

    for attempt in range(1, 4):
        subreddit = random.choice(subreddits)
        logger.info(f"Fetching story from r/{subreddit} (attempt {attempt}/3)...")

        try:
            raw = _fetch_raw_story(subreddit, min_score)
        except RuntimeError as e:
            logger.warning(str(e))
            continue

        data = _trim_with_llm(raw, max_words, min_words, cta)
        word_count = len(data["script"].split())
        logger.info(f"Script word count: {word_count}")

        if word_count >= min_words:
            logger.success(f"Reddit story script ready (r/{subreddit})")
            return data

        logger.warning(f"Script too short ({word_count} words), retrying...")

    logger.warning("Using last result despite word count.")
    return data
