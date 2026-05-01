import base64
import time

import anthropic

from config import settings

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 8192

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def call(system: str, user: str, model: str = MODEL) -> str:
    """Send a text prompt to Claude and return the response."""
    client = _get_client()
    for attempt in range(2):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text
        except anthropic.APIError:
            if attempt == 0:
                time.sleep(2)
                continue
            raise


def call_with_pdf(system: str, user: str, pdf_bytes: bytes, model: str = MODEL) -> str:
    """Send a prompt with a PDF document attached and return the response."""
    client = _get_client()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    for attempt in range(2):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[
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
                ],
            )
            return msg.content[0].text
        except anthropic.APIError:
            if attempt == 0:
                time.sleep(2)
                continue
            raise
