"""
llm_client.py
Unified LLM client with automatic provider fallback.

Provider order:
  1. Cerebras  — primary   (~450 tok/s on 70B, free, 1M tokens/day)
  2. Groq      — fallback  (~320 tok/s on 70B, free, 1K req/day)

Both use the OpenAI-compatible chat completions API so the call site is
identical. If Cerebras fails for any reason (rate limit, outage, missing key),
the call is automatically retried on Groq.

Usage:
    from llm_client import chat

    response = chat(
        messages=[{"role": "user", "content": "Hello"}],
        temperature=1.0,
    )
    text = response.choices[0].message.content
"""

import os
import logger
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Provider definitions — order = priority
# ---------------------------------------------------------------------------
_PROVIDERS = [
    {
        "name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "key_env": "CEREBRAS_API_KEY",
        "model_env": "CEREBRAS_MODEL",
        "default_model": "llama-3.3-70b",   # same capability as Groq's llama-3.3-70b-versatile
    },
    {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
    },
]


def _get_client(provider: dict):
    """Instantiate an OpenAI-compatible client for the given provider."""
    api_key = os.getenv(provider["key_env"])
    if not api_key:
        raise EnvironmentError(
            f"{provider['name']} API key not set. "
            f"Add {provider['key_env']} to your .env file."
        )
    return OpenAI(api_key=api_key, base_url=provider["base_url"])


def _get_model(provider: dict) -> str:
    """Return model name from env override or provider default."""
    return os.getenv(provider["model_env"], provider["default_model"])


def chat(messages: list, temperature: float = 1.0, max_tokens: int = 2048):
    """
    Send a chat completion request with automatic provider fallback.

    Tries each provider in order. If a provider's key is missing or the
    request fails, moves to the next one. Raises RuntimeError only if
    all providers fail.

    Args:
        messages:    OpenAI-format messages list
        temperature: Sampling temperature (default 1.0)
        max_tokens:  Max output tokens (default 2048)

    Returns:
        OpenAI ChatCompletion response object
    """
    last_error = None

    for provider in _PROVIDERS:
        try:
            client = _get_client(provider)
        except EnvironmentError as e:
            logger.warning(f"Skipping {provider['name']}: {e}")
            last_error = e
            continue

        model = _get_model(provider)
        logger.info(f"LLM → {provider['name']} ({model})")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Guard: some providers return null content on free tier
            content = response.choices[0].message.content if response.choices else None
            if not content:
                raise ValueError(f"Empty/null content returned by {provider['name']} ({model})")

            return response

        except Exception as e:
            logger.warning(f"{provider['name']} failed: {e} — trying next provider...")
            last_error = e
            continue

    raise RuntimeError(
        f"All LLM providers failed. Last error: {last_error}\n"
        "Check your API keys and internet connection."
    )
