import os

from flask import Flask, request as flask_request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from config import settings
from slack.handlers import route

bolt_app = App(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
)

flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(flask_request)


@bolt_app.event("app_mention")
def handle_mention(event, say):
    text = event.get("text", "")
    thread_ts = event.get("thread_ts") or event.get("ts")
    route(text, say, thread_ts)


@bolt_app.event("message")
def handle_message(event, say):
    # Ignore bot messages and subtypes (edits, joins, etc.)
    if event.get("bot_id") or event.get("subtype"):
        return
    # Only handle DMs here — channel mentions are caught by app_mention above
    if event.get("channel_type") == "im":
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event.get("ts")
        route(text, say, thread_ts)


def start():
    port = int(os.getenv("PORT", 3000))
    if os.getenv("ENVIRONMENT") == "production":
        from waitress import serve
        print(f"  Serving on port {port} (waitress)")
        serve(flask_app, host="0.0.0.0", port=port, threads=4)
    else:
        flask_app.run(host="0.0.0.0", port=port)
