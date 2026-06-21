"""
config.py
Loads config.json and exposes helpers for mode-aware access.

MODES:
  0 = Stock Footage  (original: Pexels + history script)
  1 = Reddit Story   (r/TIFU + gameplay background loop)
  2 = Did You Know   (LLM facts + gameplay background loop)

Set config.json → mode → active to switch.
Set config.json → mode → upgraded_subtitles to true/false for Mode-3 captions.
"""

import json
import os

_config = None


def get():
    """Return the full raw config dict."""
    global _config
    if _config is None:
        path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(path, "r") as f:
            _config = json.load(f)
    return _config


def reload():
    """Force-reload config from disk (useful for hot-switching mode)."""
    global _config
    _config = None
    return get()


def active_mode() -> int:
    """Return the currently active pipeline mode (0, 1, or 2)."""
    return int(get()["mode"]["active"])


def upgraded_subtitles() -> bool:
    """Return True if the Mode-3 upgraded subtitle style is enabled."""
    return bool(get()["mode"].get("upgraded_subtitles", True))


def mode_config() -> dict:
    """Return the config block for the active mode."""
    mode = active_mode()
    cfg = get()
    mapping = {
        0: cfg["mode0_stock_footage"],
        1: cfg["mode1_reddit_story"],
        2: cfg["mode2_did_you_know"],
    }
    if mode not in mapping:
        raise ValueError(f"Unknown mode {mode}. Set config.json → mode → active to 0, 1, or 2.")
    return mapping[mode]


def subtitle_style() -> dict:
    """Return the correct subtitle style block based on upgraded_subtitles flag."""
    cfg = get()["subtitles"]
    if upgraded_subtitles():
        return {**cfg["upgraded"], "font_path": cfg["font_path"], "whisper_model": cfg["whisper_model"], "enabled": cfg["enabled"]}
    else:
        return {**cfg["classic"], "font_path": cfg["font_path"], "whisper_model": cfg["whisper_model"], "enabled": cfg["enabled"]}
