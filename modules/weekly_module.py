import json
import re

import requests

from brain import claude_api, context_builder
from brain.checkpoints import write_brain_file, append_to_brain_file
from brain.prompts.weekly_flows import WEEKLY_FLOWS_USER_PROMPT
from clients import r2_client
from clients.moneyflows import MoneyFlowsClient
from storage import analyses, pdf_store
from storage import watchlist as watchlist_store
from storage.db import init_db

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


def _refresh_trading_brain_bmi(report_date: str):
    """Update the BMI line in TRADING_BRAIN.md after a weekly run."""
    from brain.checkpoints import read_brain_file
    latest_bmi = analyses.get_latest_bmi()
    if not latest_bmi:
        return
    brain = read_brain_file("TRADING_BRAIN.md")
    new_bmi_line = f"{latest_bmi['bmi_value']}% (as of {latest_bmi['date']})"
    brain = re.sub(
        r"(## Current BMI\n\n).*?(\n\n## )",
        rf"\g<1>{new_bmi_line}\g<2>",
        brain,
        flags=re.DOTALL,
    )
    write_brain_file("TRADING_BRAIN.md", brain)


def run() -> dict:
    """Run the Weekly Flows module end to end. Returns the parsed analysis dict."""
    init_db()
    mf = MoneyFlowsClient()

    print("[1/8] Fetching latest Weekly Flows post...")
    post = mf.get_latest_weekly_flows()
    report_date = post["date"][:10]
    pdf_url = mf.extract_pdf_url(post)
    if not pdf_url:
        raise RuntimeError("Could not extract PDF URL from Weekly Flows post")
    print(f"       report: {post.get('title', {}).get('rendered', '')} ({report_date})")
    print(f"       pdf:    {pdf_url}")

    if pdf_store.pdf_already_archived("weekly_flows", report_date):
        print("       Already processed this report — returning stored analysis.")
        latest = analyses.get_latest_analysis("weekly_flows")
        return json.loads(latest["full_output"]) if latest else {}

    print("[2/8] Uploading PDF to R2...")
    filename = f"weekly_flows_{report_date.replace('-', '_')}.pdf"
    r2_url = r2_client.upload_from_url(pdf_url, filename)
    pdf_store.store_pdf("weekly_flows", report_date, pdf_url, filename, r2_url)
    print(f"       stored: {r2_url}")

    print("[3/8] Downloading PDF for analysis...")
    pdf_bytes = requests.get(
        pdf_url,
        headers={"User-Agent": _BROWSER_UA},
        timeout=60,
    ).content
    print(f"       {len(pdf_bytes):,} bytes")

    print("[4/8] Building context...")
    context = context_builder.build_context("weekly_flows")
    print(f"       {len(context):,} chars")

    print("[5/8] Running Claude analysis (30-60s)...")
    raw = claude_api.call_with_pdf(
        system=context,
        user=WEEKLY_FLOWS_USER_PROMPT,
        pdf_bytes=pdf_bytes,
    )
    result = _parse_json(raw)
    print("       Done.")

    print("[6/8] Writing checkpoints...")
    write_brain_file("WEEKLY_CHECKPOINT.md", result["weekly_checkpoint_update"])
    append_to_brain_file("MARKET_CONDITIONS.md", result["market_conditions_entry"])

    print("[7/8] Updating DB...")
    bmi = result.get("bmi")
    if bmi is not None:
        analyses.store_bmi(report_date, float(bmi))

    analysis_id = analyses.store_analysis(
        type="weekly_flows",
        report_date=report_date,
        summary=result.get("summary", ""),
        full_output=json.dumps(result),
    )

    _refresh_trading_brain_bmi(report_date)

    print("[8/8] Posting to Slack...")
    from clients.slack_client import send_to_main
    from slack.formatter import format_report
    from storage.analyses import update_slack_ts

    slack_report = result.get("slack_report", "")
    blocks = format_report(slack_report, header=f"Weekly Flows — {report_date}")
    ts = send_to_main(text=f"Weekly Flows analysis — {report_date}", blocks=blocks)
    update_slack_ts(analysis_id, ts)
    print(f"       posted (ts={ts})")

    print("\n" + "=" * 64)
    print("WEEKLY FLOWS ANALYSIS — " + report_date)
    print("=" * 64)
    print(slack_report)
    print("=" * 64)

    return result


if __name__ == "__main__":
    run()
