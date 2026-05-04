import base64
import time

import anthropic

from config import settings

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 16000
# PDF analyses produce very large JSON — use streaming to avoid SDK's 10-min cap check
MAX_TOKENS_PDF = 32000

_client: anthropic.Anthropic | None = None

# Delays between retries (seconds). Index = attempt number (0-based).
_RETRY_DELAYS = [10, 30]


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # SDK-level retries handle transient 429/500s; we layer our own on top
        # for connection errors that the SDK sometimes re-raises immediately.
        _client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=3,
        )
    return _client


def _retry(fn):
    """Call fn() with up to 3 attempts, sleeping longer on connection errors."""
    last_exc = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            return fn()
        except anthropic.APIConnectionError as e:
            last_exc = e
            continue
        except anthropic.RateLimitError as e:
            last_exc = e
            # Rate limit: longer wait
            if attempt < len(_RETRY_DELAYS):
                time.sleep(60)
                continue
            raise
        except anthropic.APIError:
            raise
    raise last_exc


def call(system: str, user: str, model: str = MODEL) -> str:
    """Send a text prompt to Claude and return the response."""
    client = _get_client()

    def _do():
        msg = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    return _retry(_do)


def call_with_search(system: str, user: str, model: str = MODEL) -> str:
    """Send a prompt with web search enabled. Returns all text content concatenated."""
    client = _get_client()

    def _do():
        msg = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
        )
        text_parts = [block.text for block in msg.content if hasattr(block, "text")]
        return "\n".join(text_parts)

    return _retry(_do)


def call_with_pdf(system: str, user: str, pdf_bytes: bytes, model: str = MODEL) -> str:
    """Send a prompt with a PDF document attached and return the response.

    Uses streaming to support large outputs (Outlier 50 / Weekly Flows JSON
    can exceed the SDK's non-streaming 10-minute timeout guard).
    """
    client = _get_client()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64,
                    },
                },
                {"type": "text", "text": user},
            ],
        }
    ]

    def _do():
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS_PDF,
            system=system,
            messages=messages,
        ) as stream:
            return stream.get_final_text()

    return _retry(_do)
