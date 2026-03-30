"""
generator.py
Uses Groq to generate a script + YouTube metadata based on config.json settings.
"""

import os
from groq import Groq
from dotenv import load_dotenv
import logger
from config import get

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_script():
    cfg = get()
    groq_cfg = cfg["groq"]
    script_cfg = cfg["script"]

    prompt = f"""
    You are a YouTube Shorts scriptwriter. Write a highly engaging script about a surprising or shocking {script_cfg["niche"]} fact.

    Pick any historical topic you find fascinating — be creative and unexpected. Avoid repeating common topics.

    Rules:
    - Start with a hook that grabs attention in the first 3 seconds (e.g. "Did you know...")
    - Keep sentences short and punchy
    - Include 5-6 interesting points with details and context
    - End with a call to action: "{script_cfg["cta"]}"
    - Plain text only, no stage directions, no asterisks, no headers
    - YOU MUST write between {script_cfg["min_words"]} and {script_cfg["max_words"]} words for the SCRIPT section. Count carefully.

    Also provide:
    TITLE: (catchy YouTube Shorts title, max 60 chars)
    DESCRIPTION: (2-3 sentences, include #Shorts #History)
    TAGS: (10 comma-separated tags)
    SEARCH_KEYWORDS: (3 keywords to search stock footage, comma-separated)

    Format your response exactly like this:
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

    logger.info(f"Sending prompt to Groq ({groq_cfg['model']})...")

    for attempt in range(1, 4):
        response = client.chat.completions.create(
            model=groq_cfg["model"],
            temperature=groq_cfg["temperature"],
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content
        data = parse_response(raw)
        word_count = len(data["script"].split())
        logger.info(f"Script word count: {word_count} (attempt {attempt}/3)")

        if word_count >= script_cfg["min_words"]:
            return data

        logger.warning(f"Script too short ({word_count} words), retrying...")

    logger.warning("Could not hit min word count after 3 attempts, using last result.")
    return data


def parse_response(raw):
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

    return {
        "script": extract("SCRIPT"),
        "title": extract("TITLE"),
        "description": extract("DESCRIPTION"),
        "tags": [t.strip() for t in extract("TAGS").split(",")],
        "keywords": [k.strip() for k in extract("SEARCH_KEYWORDS").split(",")]
    }


if __name__ == "__main__":
    data = generate_script()
    print("SCRIPT:\n", data["script"])
    print("\nTITLE:", data["title"])
    print("KEYWORDS:", data["keywords"])
