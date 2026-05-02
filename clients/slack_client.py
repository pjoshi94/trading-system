from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import settings


def _client() -> WebClient:
    return WebClient(token=settings.SLACK_BOT_TOKEN)


def send_message(channel_id: str, text: str, blocks: list = None) -> str:
    """Send a message to a channel. Returns the message timestamp (ts)."""
    resp = _client().chat_postMessage(
        channel=channel_id.strip(),
        text=text,
        blocks=blocks,
    )
    return resp["ts"]


def send_to_main(text: str, blocks: list = None) -> str:
    return send_message(settings.SLACK_CHANNEL_ID, text, blocks)


def send_to_alerts(text: str, blocks: list = None) -> str:
    return send_message(settings.SLACK_ALERTS_CHANNEL_ID, text, blocks)


def send_reply(channel_id: str, thread_ts: str, text: str, blocks: list = None) -> str:
    """Reply in a thread. Returns the reply timestamp."""
    resp = _client().chat_postMessage(
        channel=channel_id.strip(),
        thread_ts=thread_ts,
        text=text,
        blocks=blocks,
    )
    return resp["ts"]


def verify_token() -> dict:
    """Call auth.test and return the response dict."""
    return _client().auth_test().data
