from datetime import date, timedelta

from storage import watchlist as wl_store


def run():
    """
    Evening check: notify about tickers with earnings tomorrow.
    Posts to #trading-alerts with Block Kit buttons (if RAILWAY_URL set)
    or plain text (fallback).
    """
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    items = wl_store.get_watchlist_by_earnings_date(tomorrow)

    if not items:
        return

    from clients.slack_client import send_to_alerts
    from config import settings

    for item in items:
        ticker = item["ticker"]
        conviction = item.get("conviction") or "—"
        text = f":bell: *{ticker}* reports earnings tomorrow ({tomorrow}) | conviction: {conviction}"

        if settings.RAILWAY_URL:
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text},
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Queue Deep Dive"},
                            "action_id": "queue_deep_dive",
                            "value": ticker,
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Dismiss"},
                            "action_id": "dismiss_deep_dive",
                            "value": ticker,
                        },
                    ],
                },
            ]
            send_to_alerts(text=text, blocks=blocks)
        else:
            send_to_alerts(text=text)

    print(f"[earnings_night] Notified {len(items)} ticker(s) with earnings tomorrow.")
