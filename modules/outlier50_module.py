import json
import re
import sqlite3
import time
from datetime import date

import requests

from brain import claude_api, context_builder
from brain.checkpoints import write_brain_file
from brain.prompts.outlier50 import OUTLIER50_USER_PROMPT
from clients import r2_client
from clients.moneyflows import MoneyFlowsClient
from storage import analyses, pdf_store
from storage import watchlist as watchlist_store
from storage.db import init_db

def _lookup_earnings_bulk(tickers: list[str]):
    """Look up earnings dates for a batch of tickers. Sleeps 3s between calls if >3 tickers."""
    from clients.earnings import lookup_earnings_date, compute_earnings_block_dates

    for i, ticker in enumerate(tickers):
        if i > 0 and len(tickers) > 3:
            time.sleep(3)
        print(f"       Earnings lookup: {ticker}...")
        try:
            result = lookup_earnings_date(ticker)
            if result["status"] in ("found", "low_confidence") and result["earnings_date"]:
                dates = compute_earnings_block_dates(result["earnings_date"])
                watchlist_store.update_earnings_dates(
                    ticker=ticker,
                    earnings_date=result["earnings_date"],
                    pre_earnings_block_starts=dates["pre_earnings_block_starts"],
                    entry_window_opens=dates["entry_window_opens"],
                    earnings_confidence=result["confidence"],
                )
                print(f"         {ticker}: earnings {result['earnings_date']} ({result['confidence']})")
            else:
                print(f"         {ticker}: not found")
        except Exception as e:
            print(f"         {ticker}: lookup failed — {e}")


_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _parse_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Could not parse JSON from Claude response")


def _apply_watchlist_updates(updates: list, report_date: str) -> list[str]:
    """Apply watchlist updates from Claude analysis. Returns list of new/updated tickers."""
    affected = []
    for update in updates:
        ticker = update.get("ticker", "").upper()
        action = update.get("action")
        if not ticker or not action:
            continue
        if action == "add":
            try:
                watchlist_store.add_to_watchlist(
                    ticker=ticker,
                    added_date=report_date,
                    outlier_rank=update.get("outlier_rank"),
                    conviction=update.get("conviction"),
                    sector=update.get("sector"),
                    notes=update.get("notes"),
                )
            except sqlite3.IntegrityError:
                watchlist_store.update_watchlist_item(
                    ticker=ticker,
                    outlier_rank=update.get("outlier_rank"),
                    conviction=update.get("conviction"),
                    notes=update.get("notes"),
                )
            affected.append(ticker)
        elif action == "update":
            watchlist_store.update_watchlist_item(
                ticker=ticker,
                outlier_rank=update.get("outlier_rank"),
                conviction=update.get("conviction"),
                notes=update.get("notes"),
            )
            affected.append(ticker)
        elif action == "remove":
            watchlist_store.remove_from_watchlist(ticker)
    return affected


def _refresh_trading_brain(report_date: str):
    from storage import positions as pos_store

    items = watchlist_store.get_watchlist()
    positions = pos_store.get_open_positions()
    latest_bmi = analyses.get_latest_bmi()

    bmi_line = (
        f"{latest_bmi['bmi_value']}% (as of {latest_bmi['date']})"
        if latest_bmi
        else "Unknown — awaiting first Weekly Flows analysis."
    )

    if positions:
        pos_rows = [
            "| Ticker | Shares | Entry | Date | Stop | Target |",
            "|--------|--------|-------|------|------|--------|",
        ]
        for p in positions:
            target_low = round(p["entry_price"] * 1.20, 2)
            target_high = round(p["entry_price"] * 1.25, 2)
            pos_rows.append(
                f"| {p['ticker']} | {p['shares']} | ${p['entry_price']:.2f} | "
                f"{p['entry_date']} | ${p['stop_loss']:.2f} | "
                f"${target_low:.2f}–${target_high:.2f} |"
            )
        positions_section = "\n".join(pos_rows)
    else:
        positions_section = "No open positions."

    if items:
        rows = ["| Ticker | Rank | Conviction | Sector | Notes |",
                "|--------|------|------------|--------|-------|"]
        for item in items:
            rows.append(
                f"| {item['ticker']} "
                f"| {item.get('outlier_rank') or '-'} "
                f"| {item.get('conviction') or '-'} "
                f"| {item.get('sector') or '-'} "
                f"| {(item.get('notes') or '')[:60]} |"
            )
        watchlist_section = "\n".join(rows)
    else:
        watchlist_section = "None."

    content = f"""# TRADING BRAIN — Current State Snapshot

Last updated: {date.today().isoformat()}

## Open Positions

{positions_section}

## Watchlist

{watchlist_section}

## Current BMI

{bmi_line}

## Market Bias

[Update after each Weekly Flows analysis.]

## Active Rules

- Do not enter new positions when BMI > 80%
- All entries and exits executed manually on Fidelity
"""
    write_brain_file("TRADING_BRAIN.md", content)


def run() -> dict:
    """Run the Outlier 50 module end to end. Returns the parsed analysis dict."""
    init_db()
    mf = MoneyFlowsClient()

    print("[1/7] Fetching latest Outlier 50 post...")
    post = mf.get_latest_outlier50()
    report_date = post["date"][:10]
    pdf_url = mf.extract_pdf_url(post)
    if not pdf_url:
        raise RuntimeError("Could not extract PDF URL from Outlier 50 post")
    print(f"       report: {post.get('title', {}).get('rendered', '')} ({report_date})")
    print(f"       pdf:    {pdf_url}")

    if pdf_store.pdf_already_archived("outlier50", report_date):
        print("       Already processed this report — returning stored analysis.")
        latest = analyses.get_latest_analysis("outlier50")
        return json.loads(latest["full_output"]) if latest else {}

    print("[2/7] Uploading PDF to R2...")
    year_month = report_date[:7].replace("-", "_")
    filename = f"outlier50_{year_month}.pdf"
    r2_url = r2_client.upload_from_url(pdf_url, filename)
    pdf_store.store_pdf("outlier50", report_date, pdf_url, filename, r2_url)
    print(f"       stored: {r2_url}")

    print("[3/7] Downloading PDF for analysis...")
    pdf_bytes = requests.get(
        pdf_url,
        headers={"User-Agent": _BROWSER_UA},
        timeout=60,
    ).content
    print(f"       {len(pdf_bytes):,} bytes")

    print("[4/7] Building context...")
    context = context_builder.build_context("outlier50")
    print(f"       {len(context):,} chars")

    print("[5/7] Running Claude analysis (30-60s)...")
    raw = claude_api.call_with_pdf(
        system=context,
        user=OUTLIER50_USER_PROMPT,
        pdf_bytes=pdf_bytes,
    )
    result = _parse_json(raw)
    print("       Done.")

    print("[6/7] Writing checkpoints and updating DB...")
    write_brain_file("OUTLIER50_CHECKPOINT.md", result["checkpoint_update"])

    affected_tickers = _apply_watchlist_updates(result.get("watchlist_updates", []), report_date)

    if result.get("bmi") is not None:
        analyses.store_bmi(report_date, float(result["bmi"]))

    if affected_tickers:
        print(f"       Looking up earnings dates for {len(affected_tickers)} ticker(s)...")
        _lookup_earnings_bulk(affected_tickers)

    analysis_id = analyses.store_analysis(
        type="outlier50",
        report_date=report_date,
        summary=result.get("summary", ""),
        full_output=json.dumps(result),
    )

    print("[7/8] Refreshing TRADING_BRAIN.md...")
    _refresh_trading_brain(report_date)

    print("[8/8] Posting to Slack...")
    from clients.slack_client import send_to_main
    from slack.formatter import format_report
    from storage.analyses import update_slack_ts

    slack_report = result.get("slack_report", "")
    blocks = format_report(slack_report, header=f"Outlier 50 — {report_date}")
    ts = send_to_main(text=f"Outlier 50 analysis — {report_date}", blocks=blocks)
    update_slack_ts(analysis_id, ts)
    print(f"       posted (ts={ts})")

    print("\n" + "=" * 64)
    print("OUTLIER 50 ANALYSIS — " + report_date)
    print("=" * 64)
    print(slack_report)
    print("=" * 64)

    return result


if __name__ == "__main__":
    run()
