"""
config.py
Loads config.json and exposes it as a simple dict.
"""

import json
import os

_config = None

def get():
    global _config
    if _config is None:
        path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(path, "r") as f:
            _config = json.load(f)
    return _config
