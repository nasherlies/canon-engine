"""OpenAI-compatible API client for Canon Engine.

Thin wrapper around the ``openai`` library that handles:

* Loading API keys from environment variables (``CANON_LLM_API_KEY``,
  ``OPENAI_API_KEY``, ``OPENROUTER_API_KEY``).
* Base-URL swapping for OpenRouter and other compatible providers.
* Chat-completion with retries, exponential back-off, and structured errors.

Public API
----------
* ``MissingAPIKeyError`` – raised when no API key is configured.
* ``chat_completion(messages, model=None, max_tokens=None) -> str``
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Sequence

import openai
from openai import OpenAI

from canon_engine.config import config
from canon_engine.constants import MAX_NARRATIVE_TOKENS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default model used when the caller doesn't specify one.
DEFAULT_MODEL: str = "gpt-4o-mini"

#: Model used for major story beats (boss fights, world-shaking events).
PREMIUM_MODEL: str = "gpt-4o"

#: OpenRouter base URL (used when provider is "openrouter").
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

#: Maximum retries on transient errors.
MAX_RETRIES: int = 3

#: Base delay (seconds) for exponential back-off.
RETRY_BASE_DELAY: float = 1.0

#: Cap on per-request timeout (seconds).
REQUEST_TIMEOUT: float = 60.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MissingAPIKeyError(RuntimeError):
    """Raised when no API key is available for the configured provider."""

    def __init__(self, provider: str = "openai") -> None:
        self.provider = provider
        super().__init__(
            f"No API key found for provider '{provider}'. "
            f"Set CANON_LLM_API_KEY, OPENAI_API_KEY, or OPENROUTER_API_KEY "
            f"in your environment or .env file."
        )


# ---------------------------------------------------------------------------
# Client factory (lazy singleton)
# ---------------------------------------------------------------------------

_client: Optional[OpenAI] = None


def _resolve_api_key() -> str:
    """Return the first non-empty API key found in the environment.

    Search order:
    1. ``CANON_LLM_API_KEY`` (Canon-specific)
    2. ``OPENROUTER_API_KEY`` (if provider is openrouter)
    3. ``OPENAI_API_KEY`` (generic fallback)
    """
    # Config dataclass already reads CANON_LLM_API_KEY
    key = config.llm_api_key.strip()
    if key:
        return key

    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key:
        return key

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key

    provider = config.llm_provider
    raise MissingAPIKeyError(provider)


def _resolve_base_url() -> Optional[str]:
    """Return the base URL override for non-default providers."""
    provider = config.llm_provider.lower()
    if provider in ("openrouter",):
        return OPENROUTER_BASE_URL
    # Check explicit env override.
    explicit = os.getenv("CANON_LLM_BASE_URL", "").strip()
    if explicit:
        return explicit
    return None


def get_client() -> OpenAI:
    """Return (and lazily create) the shared ``OpenAI`` client singleton."""
    global _client
    if _client is not None:
        return _client

    api_key = _resolve_api_key()
    base_url = _resolve_base_url()

    kwargs: Dict[str, Any] = {"api_key": api_key, "timeout": REQUEST_TIMEOUT}
    if base_url is not None:
        kwargs["base_url"] = base_url
        logger.info("Using base_url=%s for provider %s", base_url, config.llm_provider)

    _client = OpenAI(**kwargs)
    logger.info("OpenAI client initialised (provider=%s, model=%s).",
                config.llm_provider, config.llm_model)
    return _client


def reset_client() -> None:
    """Tear down the cached client (useful in tests)."""
    global _client
    _client = None


# ---------------------------------------------------------------------------
# Core completion
# ---------------------------------------------------------------------------


def chat_completion(
    messages: Sequence[Dict[str, str]],
    *,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: float = 0.9,
    response_format: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Send a chat-completion request and return the assistant's text.

    Parameters
    ----------
    messages : sequence of dict
        OpenAI-style message list (``[{"role": "system", "content": "…"}, …]``).
    model : str, optional
        Model identifier.  Falls back to ``config.llm_model``, then
        :pydata:`DEFAULT_MODEL`.
    max_tokens : int, optional
        Maximum tokens to generate.  Defaults to ``MAX_NARRATIVE_TOKENS``.
    temperature : float
        Sampling temperature (default 0.9 for creative narration).
    response_format : dict, optional
        Structured output format (e.g. ``{"type": "json_object"}``).
    extra : dict, optional
        Additional keyword arguments forwarded to ``client.chat.completions.create``.

    Returns
    -------
    str
        The assistant's response text (content of the first choice).

    Raises
    ------
    MissingAPIKeyError
        If no API key is configured.
    openai.RateLimitError
        After exhausting retries on a 429.
    openai.APIError
        After exhausting retries on server errors.
    """
    client = get_client()

    resolved_model = model or config.llm_model or DEFAULT_MODEL
    resolved_max_tokens = max_tokens if max_tokens is not None else MAX_NARRATIVE_TOKENS

    kwargs: Dict[str, Any] = {
        "model": resolved_model,
        "messages": list(messages),
        "max_tokens": resolved_max_tokens,
        "temperature": temperature,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if extra:
        kwargs.update(extra)

    # Retry loop with exponential back-off.
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(
                "chat_completion attempt %d/%d model=%s msgs=%d max_tokens=%d",
                attempt, MAX_RETRIES, resolved_model, len(messages), resolved_max_tokens,
            )
            t0 = time.monotonic()
            response = client.chat.completions.create(**kwargs)
            elapsed = time.monotonic() - t0
            logger.info("chat_completion model=%s tokens≈%d elapsed=%.2fs",
                        resolved_model, resolved_max_tokens, elapsed)

            text = response.choices[0].message.content or ""
            return text.strip()

        except openai.RateLimitError as exc:
            last_exc = exc
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning("Rate-limited (attempt %d/%d). Retrying in %.1fs…",
                           attempt, MAX_RETRIES, delay)
            time.sleep(delay)

        except openai.APIStatusError as exc:
            last_exc = exc
            # Only retry on 5xx (server) errors; raise immediately on 4xx.
            if 400 <= exc.status_code < 500:
                logger.error("Non-retryable API error (status %d): %s",
                             exc.status_code, exc)
                raise
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning("API error (attempt %d/%d, status %d): %s. Retrying in %.1fs…",
                           attempt, MAX_RETRIES, exc.status_code, exc, delay)
            time.sleep(delay)

        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            last_exc = exc
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning("API error (attempt %d/%d): %s. Retrying in %.1fs…",
                           attempt, MAX_RETRIES, exc, delay)
            time.sleep(delay)

    # All retries exhausted.
    if last_exc is not None:
        raise last_exc  # type: ignore[misc]
    raise RuntimeError("chat_completion failed with no exception captured")  # pragma: no cover


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def resolve_model(premium: bool = False) -> str:
    """Return the model identifier for a narration request.

    Parameters
    ----------
    premium : bool
        If ``True``, return the premium model for major story beats.

    Returns
    -------
    str
        Model identifier string.
    """
    if premium:
        return config.llm_model if config.llm_model else PREMIUM_MODEL
    return config.llm_model if config.llm_model else DEFAULT_MODEL
