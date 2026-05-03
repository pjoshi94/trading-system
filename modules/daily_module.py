import json
import re
from datetime import date

from brain import claude_api, context_builder
from brain.checkpoints import append_to_brain_file
from brain.prompts.daily_check import DAILY_CHECK_USER_PROMPT
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


def _post_urgent_alerts(result: dict, report_date: str):
    """Post urgent alerts to #trading-alerts when has_urgent_alerts is true."""
    if not result.get("has_urgent_alerts"):
        return
    from clients.slack_client import send_to_alerts
    from slack.formatter import format_report

    # Build alert text from positions flagged as urgent
    lines = [f"🚨 *Trading Alerts — {report_date}*\n"]
    for pos in result.get("positions", []):
        if pos.get("urgent_alert_required"):
            ticker = pos["ticker"]
            close = pos.get("today_close", "?")
            chg = pos.get("day_change_pct", 0)
            verdict = pos.get("verdict", "")
            thesis = pos.get("thesis_status", "")
            lines.append(f"• *{ticker}* ${close} ({chg:+.1f}%) — {verdict} / thesis {thesis}")
            summary = pos.get("position_summary", "")
            if summary:
                lines.append(f"  {summary}")

    text = "\n".join(lines)
    blocks = format_report(text, header=f"Urgent Alerts — {report_date}")
    send_to_alerts(text=f"Urgent trading alert — {report_date}", blocks=blocks)
    print(f"       urgent alert posted to #trading-alerts")


def _run_auto_tier1(today: str):
    """Fire Tier 1 on any watchlist entry whose entry_window_opens = today."""
    ready = wl_store.get_entry_window_ready(today)
    if not ready:
        return
    print(f"       Auto Tier 1 for {len(ready)} ticker(s): {[r['ticker'] for r in ready]}")
    from modules.stock_module import run_tier1
    from clients.slack_client import send_to_main
    from slack.formatter import format_report
    from storage.analyses import update_slack_ts

    for item in ready:
        ticker = item["ticker"]
        try:
            result = run_tier1(ticker)
            blocks = format_report(
                result["slack_summary"],
                header=f"Auto Tier 1: {ticker} — entry window now open",
            )
            ts = send_to_main(
                text=f"Entry window open for {ticker} — auto Tier 1 complete. Reply `deep dive` for full analysis.",
                blocks=blocks,
            )
            if result["analysis_id"]:
                update_slack_ts(result["analysis_id"], ts)
            wl_store.update_watchlist_item(ticker, deep_dive_queued=0)
        except Exception as e:
            print(f"       Auto Tier 1 for {ticker} failed: {e}")


def run() -> dict:
    """Run the nightly check module. Returns the parsed result dict."""
    init_db()
    today = date.today().isoformat()

    print(f"[0/5] Checking entry windows ({today})...")
    _run_auto_tier1(today)

    print(f"[1/5] Loading positions and watchlist ({today})...")
    positions = pos_store.get_open_positions()
    watchlist = wl_store.get_watchlist()
    print(f"       {len(positions)} open position(s), {len(watchlist)} watchlist item(s)")

    print("[2/5] Running Claude nightly check (with web search)...")
    context = context_builder.build_context("daily_check")
    user_prompt = DAILY_CHECK_USER_PROMPT.format(today_date=today)
    raw = claude_api.call_with_search(system=context, user=user_prompt)
    result = _parse_json(raw)
    print("       Done.")

    print("[3/5] Writing to DB and checkpoints...")
    market_append = result.get("market_conditions_append")
    if market_append:
        append_to_brain_file("MARKET_CONDITIONS.md", market_append)

    slack_summary = result.get("slack_summary", "")
    analysis_id = analyses.store_analysis(
        type="daily_check",
        report_date=today,
        summary=result.get("market", {}).get("market_one_liner", ""),
        slack_summary=slack_summary,
        full_analysis=json.dumps(result),
    )

    print("[4/5] Posting to Slack...")
    from clients.slack_client import send_to_main
    from slack.formatter import format_report
    from storage.analyses import update_slack_ts

    blocks = format_report(slack_summary, header=f"Nightly Check — {today}")
    ts = send_to_main(text=f"Nightly check — {today}", blocks=blocks)
    update_slack_ts(analysis_id, ts)
    print(f"       posted (ts={ts})")

    print("[5/5] Checking for urgent alerts...")
    _post_urgent_alerts(result, today)

    print("\n" + "=" * 64)
    print("NIGHTLY CHECK — " + today)
    print("=" * 64)
    print(slack_summary)
    print("=" * 64)

    return result


if __name__ == "__main__":
    run()
