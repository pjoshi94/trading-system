import os
import re

from flask import Flask, request as flask_request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from config import settings
from slack.handlers import route, is_thread_keyword

bolt_app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
)

flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(flask_request)


@flask_app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    return handler.handle(flask_request)


@bolt_app.event("app_mention")
def handle_mention(event, say):
    text = event.get("text", "")
    thread_ts = event.get("thread_ts") or event.get("ts")
    route(text, say, thread_ts)


@bolt_app.event("message")
def handle_message(event, say):
    if event.get("bot_id") or event.get("subtype"):
        return

    channel_type = event.get("channel_type")
    text = event.get("text", "")
    thread_ts = event.get("thread_ts")
    ts = event.get("ts")

    if channel_type == "im":
        route(text, say, thread_ts or ts)
    elif thread_ts and thread_ts != ts:
        # Thread reply in a channel — only handle recognized thread keywords
        if is_thread_keyword(text):
            route(text, say, thread_ts)


@bolt_app.action("queue_deep_dive")
def handle_queue_deep_dive(ack, body, say):
    ack()
    ticker = body["actions"][0]["value"].upper()
    try:
        from storage import watchlist as wl_store
        wl_store.update_watchlist_item(ticker, deep_dive_queued=1)
        say(f":white_check_mark: *{ticker}* queued — Tier 1 will run automatically when the entry window opens.")
    except Exception as e:
        say(f":x: Failed to queue {ticker}: {e}")


@bolt_app.action("dismiss_deep_dive")
def handle_dismiss_deep_dive(ack, body, say):
    ack()
    ticker = body["actions"][0]["value"].upper()
    say(f":x: Dismissed earnings deep dive for *{ticker}*.")


def start():
    port = int(os.getenv("PORT", 3000))
    if os.getenv("ENVIRONMENT") == "production":
        from waitress import serve
        print(f"  Serving on port {port} (waitress)")
        serve(flask_app, host="0.0.0.0", port=port, threads=4)
    else:
        flask_app.run(host="0.0.0.0", port=port)
