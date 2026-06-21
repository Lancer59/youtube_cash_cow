"""
generator.py
Mode 0 & Mode 2 script generation.

  Mode 0 — History narration (original pipeline)
  Mode 2 — "Did You Know" shocking facts (LLM-generated, no stock footage needed)

Both modes pull topics from topics.json to avoid repeating the same subject.
LLM calls go through llm_client.py: Cerebras primary → Groq fallback.
"""

import os
from dotenv import load_dotenv
import logger
from config import get, mode_config
from topics import next_topic, mark_failed, peek_queue_size
from llm_client import chat

load_dotenv()


# ---------------------------------------------------------------------------
# MODE 0 — Original history script
# ---------------------------------------------------------------------------

def generate_script() -> dict:
    """Generate a history narration script (Mode 0), using topics.json queue."""
    cfg = get()
    groq_cfg = cfg["groq"]
    script_cfg = mode_config()  # mode0_stock_footage block

    min_words = script_cfg["script"]["min_words"]
    max_words = script_cfg["script"]["max_words"]
    cta = script_cfg["script"]["cta"]

    # Pull next topic from the shared queue
    topic_entry = next_topic()
    topic = topic_entry["topic"]
    hint  = topic_entry["hint"]
    remaining = peek_queue_size()
    logger.info(f"Topics remaining in queue: {remaining}")

    prompt = f"""
You are a YouTube Shorts scriptwriter. Write a highly engaging script about this specific history topic:

TOPIC: {topic}
CONTEXT HINT: {hint}

Rules:
- Start with a hook that grabs attention in the first 3 seconds (e.g. "Did you know...")
- Keep sentences short and punchy
- Structure: Hook → Build tension with 5-6 interesting points → Twist or payoff → CTA
- End with: "{cta}"
- Plain text only — no stage directions, no asterisks, no headers
- YOU MUST write between {min_words} and {max_words} words for the SCRIPT section. Count carefully.

Also provide:
TITLE: (catchy YouTube Shorts title, max 60 chars)
DESCRIPTION: (2-3 sentences, include #Shorts #History)
TAGS: (10 comma-separated tags)
SEARCH_KEYWORDS: (3 keywords to search stock footage, comma-separated)

Format exactly like this:
SCRIPT:
<the script here>

TITLE:
<title here>

DESCRIPTION:
<description here>

TAGS:
<tags here>

SEARCH_KEYWORDS:
<keywords here>
"""

    logger.info(f"Generating script — topic: {topic}...")

    data = {}
    for attempt in range(1, 4):
        response = chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=groq_cfg["temperature"],
        )
        raw = response.choices[0].message.content or ""
        data = _parse_response(raw, include_keywords=True)
        word_count = len(data["script"].split())
        logger.info(f"Script word count: {word_count} (attempt {attempt}/3)")

        if word_count >= min_words:
            data["description"] = generate_description(data["title"], data["script"], data["tags"])
            return data

        logger.warning(f"Script too short ({word_count} words), retrying...")

    logger.warning("Could not hit min word count after 3 attempts, using last result.")
    if not data.get("script"):
        mark_failed(topic_entry)
    else:
        data["description"] = generate_description(data["title"], data["script"], data["tags"])
    return data


# ---------------------------------------------------------------------------
# MODE 2 — "Did You Know" facts
# ---------------------------------------------------------------------------

def generate_did_you_know_script() -> dict:
    """Generate a shocking-facts narration script (Mode 2), using topics.json queue."""
    cfg = get()
    groq_cfg = cfg["groq"]
    m2 = mode_config()  # mode2_did_you_know block

    facts_per_video = m2["facts_per_video"]
    min_words = m2["min_words"]
    max_words = m2["max_words"]
    cta = m2["cta"]

    # Pull next topic from the shared queue (same queue as Mode 0)
    topic_entry = next_topic()
    topic = topic_entry["topic"]
    hint  = topic_entry["hint"]
    remaining = peek_queue_size()
    logger.info(f"Topics remaining in queue: {remaining}")

    prompt = f"""
You are a YouTube Shorts scriptwriter specializing in mind-blowing facts.
Write a "Did You Know" facts script for a YouTube Short, focused on this specific topic:

TOPIC: {topic}
CONTEXT HINT: {hint}

Rules:
- Start with the most shocking fact from this topic as a hook (e.g. "Did you know...")
- Include exactly {facts_per_video} surprising, counterintuitive facts about the topic
- Each fact gets 1-2 punchy sentences. No filler.
- Build curiosity — make each fact feel MORE surprising than the last
- End with: "{cta}"
- Plain text only — no asterisks, headers, numbering, or emojis
- YOU MUST write between {min_words} and {max_words} words. Count carefully.

Also provide:
TITLE: (catchy YouTube Shorts title, max 60 chars)
DESCRIPTION: (2-3 sentences, include #Shorts #DidYouKnow)
TAGS: (10 comma-separated tags)

Format exactly like this:
SCRIPT:
<the script here>

TITLE:
<title here>

DESCRIPTION:
<description here>

TAGS:
<tags here>
"""

    logger.info(f"Generating 'Did You Know' script — topic: {topic}...")

    data = {}
    for attempt in range(1, 4):
        response = chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=groq_cfg["temperature"],
        )
        raw = response.choices[0].message.content or ""
        data = _parse_response(raw, include_keywords=False)
        word_count = len(data["script"].split())
        logger.info(f"Script word count: {word_count} (attempt {attempt}/3)")

        if word_count >= min_words:
            data["description"] = generate_description(data["title"], data["script"], data["tags"])
            return data

        logger.warning(f"Script too short ({word_count} words), retrying...")

    logger.warning("Could not hit min word count after 3 attempts, using last result.")
    if not data.get("script"):
        mark_failed(topic_entry)
    else:
        data["description"] = generate_description(data["title"], data["script"], data["tags"])
    return data


# ---------------------------------------------------------------------------
# Second LLM call — full description + hashtags
# ---------------------------------------------------------------------------

def generate_description(title: str, script: str, tags: list) -> str:
    """
    Second LLM call: takes the finished script + title and returns a full
    YouTube video description with intro, key points, CTA, and hashtags.
    """
    tags_str = ", ".join(tags) if tags else ""

    prompt = f"""
You are a YouTube SEO specialist. Write a complete, optimized YouTube video description for a YouTube Short.

VIDEO TITLE: {title}

SCRIPT (the narration):
{script}

EXISTING TAGS: {tags_str}

Instructions:
1. Write a compelling INTRO paragraph (2-3 sentences) that summarizes what the video covers and hooks the viewer. Do NOT start with "In this video".
2. Write a KEY POINTS section (3-5 bullet points using •) that previews the most interesting facts or moments.
3. Write a CTA line encouraging viewers to like, comment, follow, and turn on notifications.
4. Write a HASHTAGS block at the very end with 25 relevant hashtags on a single line, separated by spaces. Mix broad (#Shorts #YouTube) and niche-specific tags. Always include #Shorts.

Format your response EXACTLY like this:

INTRO:
<intro paragraph>

KEY_POINTS:
<bullet points>

CTA:
<call to action line>

HASHTAGS:
<all hashtags on one line>
"""

    logger.info("Generating full description + hashtags (second LLM call)...")

    try:
        response = chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw = response.choices[0].message.content or ""
        description = _parse_description(raw)
        logger.success("Description generated")
        return description
    except Exception as e:
        logger.warning(f"Description generation failed: {e} — falling back to basic description")
        hashtags = " ".join(f"#{t.replace(' ', '')}" for t in tags[:10]) if tags else "#Shorts"
        return f"{title}\n\n{hashtags} #Shorts"


def _parse_description(raw: str) -> str:
    """Assembles the full description string from the second LLM response."""
    if not raw:
        return ""

    def extract(label):
        try:
            start = raw.index(f"{label}:") + len(f"{label}:")
            all_labels = ["INTRO:", "KEY_POINTS:", "CTA:", "HASHTAGS:"]
            end = len(raw)
            for lbl in all_labels:
                if lbl in raw and raw.index(lbl) > raw.index(f"{label}:"):
                    pos = raw.index(lbl)
                    if pos < end:
                        end = pos
            return raw[start:end].strip()
        except ValueError:
            return ""

    intro      = extract("INTRO")
    key_points = extract("KEY_POINTS")
    cta        = extract("CTA")
    hashtags   = extract("HASHTAGS")

    parts = []
    if intro:
        parts.append(intro)
    if key_points:
        parts.append(key_points)
    if cta:
        parts.append(cta)
    if hashtags:
        # Ensure hashtags are on their own block at the bottom
        parts.append(hashtags)

    if not parts:
        logger.warning("Description parser found no sections — returning raw response")
        return raw.strip()

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Shared parser
# ---------------------------------------------------------------------------

def _parse_response(raw: str, include_keywords: bool = True) -> dict:
    """Parse LLM response. Returns empty-field dict if raw is None or malformed."""
    if not raw:
        return {"script": "", "title": "", "description": "", "tags": [], "keywords": []}

    def extract(label):
        try:
            start = raw.index(f"{label}:") + len(f"{label}:")
            next_labels = ["TITLE:", "DESCRIPTION:", "TAGS:", "SEARCH_KEYWORDS:"]
            end = len(raw)
            for lbl in next_labels:
                if lbl in raw and raw.index(lbl) > raw.index(f"{label}:"):
                    pos = raw.index(lbl)
                    if pos < end:
                        end = pos
            return raw[start:end].strip()
        except ValueError:
            return ""

    result = {
        "script": extract("SCRIPT"),
        "title": extract("TITLE"),
        "description": extract("DESCRIPTION"),
        "tags": [t.strip() for t in extract("TAGS").split(",") if t.strip()],
        "keywords": []
    }
    if include_keywords:
        result["keywords"] = [k.strip() for k in extract("SEARCH_KEYWORDS").split(",") if k.strip()]
    return result


if __name__ == "__main__":
    from config import active_mode
    mode = active_mode()
    if mode == 0:
        data = generate_script()
    elif mode == 2:
        data = generate_did_you_know_script()
    else:
        print("generator.py handles modes 0 and 2. For mode 1, use reddit_story.py")
        exit()
    print("SCRIPT:\n", data["script"])
    print("\nTITLE:", data["title"])
