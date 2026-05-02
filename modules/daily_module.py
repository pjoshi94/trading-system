import json
import re
from datetime import date

from brain import claude_api, context_builder
from brain.checkpoints import append_to_brain_file
from brain.prompts.daily_check import DAILY_CHECK_SYSTEM_PROMPT, DAILY_CHECK_USER_PROMPT
from storage import analyses
from storage import positions as pos_store
from storage import watchlist as wl_store
from storage.db import init_db


def _parse_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Could not parse JSON from Claude response")


def _fetch_price_data(positions: list, watchlist: list) -> str:
    """Use Claude's web search to get current prices and moves."""
    tickers = []
    if positions:
        tickers += [p["ticker"] for p in positions]
    if watchlist:
        tickers += [w["ticker"] for w in watchlist[:10]]  # top 10 watchlist only

    if not tickers:
        return "No positions or watchlist items to check."

    ticker_list = ", ".join(tickers)
    query = (
        f"Current stock prices and today's percentage change for: {ticker_list}. "
        f"Also include S&P 500 and VIX levels."
    )

    result = claude_api.call(
        system="You are a financial data assistant. Search the web for current market data and return a concise summary.",
        user=query,
    )
    return result


def _fetch_macro_news() -> str:
    """Use Claude's web search to get today's macro news."""
    result = claude_api.call(
        system="You are a macro market analyst. Search the web for today's key market-moving news.",
        user=(
            "What are the most important macro news items from today that could affect "
            "equity markets? Focus on Fed, inflation, geopolitics, and major sector events. "
            "Be concise — 3-5 bullet points max."
        ),
    )
    return result


def _post_alerts(alerts: list, report_date: str):
    """Post urgent alerts to #trading-alerts channel."""
    if not alerts:
        return
    from clients.slack_client import send_to_alerts
    from slack.formatter import format_report

    lines = [f"*Alerts — {report_date}*\n"]
    for alert in alerts:
        ticker = f"*{alert['ticker']}* — " if alert.get("ticker") else ""
        lines.append(f"• {ticker}{alert['message']}")

    text = "\n".join(lines)
    blocks = format_report(text, header=f"Alerts — {report_date}")
    send_to_alerts(text=f"Trading alert — {report_date}", blocks=blocks)
    print(f"       {len(alerts)} alert(s) posted to #trading-alerts")


def run() -> dict:
    """Run the nightly check module. Returns the parsed result dict."""
    init_db()
    today = date.today().isoformat()

    print(f"[1/6] Loading positions and watchlist ({today})...")
    positions = pos_store.get_open_positions()
    watchlist = wl_store.get_watchlist()
    print(f"       {len(positions)} open position(s), {len(watchlist)} watchlist item(s)")

    print("[2/6] Fetching price data (web search)...")
    price_data = _fetch_price_data(positions, watchlist)
    print(f"       {len(price_data)} chars")

    print("[3/6] Fetching macro news (web search)...")
    macro_summary = _fetch_macro_news()
    print(f"       {len(macro_summary)} chars")

    print("[4/6] Running Claude nightly check...")
    context = context_builder.build_context("daily_check")
    user_prompt = DAILY_CHECK_USER_PROMPT.format(
        date=today,
        price_data=price_data,
        macro_summary=macro_summary,
    )
    raw = claude_api.call(system=context, user=user_prompt)
    result = _parse_json(raw)
    print("       Done.")

    print("[5/6] Writing to DB and checkpoints...")
    if result.get("significant") and result.get("market_conditions_entry"):
        append_to_brain_file("MARKET_CONDITIONS.md", result["market_conditions_entry"])

    analyses.store_analysis(
        type="daily_check",
        report_date=today,
        summary=result.get("summary", ""),
        full_output=json.dumps(result),
    )

    print("[6/6] Posting to Slack...")
    from clients.slack_client import send_to_main
    from slack.formatter import format_report
    from storage.analyses import update_slack_ts

    slack_report = result.get("slack_report", "")
    blocks = format_report(slack_report, header=f"Nightly Check — {today}")
    ts = send_to_main(text=f"Nightly check — {today}", blocks=blocks)
    update_slack_ts(
        analyses.get_latest_analysis("daily_check")["id"],
        ts,
    )
    print(f"       posted (ts={ts})")

    # Post alerts to #trading-alerts if any
    alerts = result.get("alerts", [])
    urgent = [
        a for a in alerts
        if a.get("type") in ("stop_loss_near", "big_move", "bmi_threshold")
    ]
    if urgent:
        _post_alerts(urgent, today)

    print("\n" + "=" * 64)
    print("NIGHTLY CHECK — " + today)
    print("=" * 64)
    print(slack_report)
    print("=" * 64)

    return result


if __name__ == "__main__":
    run()
