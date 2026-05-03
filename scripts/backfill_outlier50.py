"""
One-time script to backfill the Outlier 50 checkpoint with historical reports.
Fetches pages 2-13 from MoneyFlows (oldest to newest), processes each through
Claude, and builds up a cumulative checkpoint. Skips Slack posting.

Run from repo root: python scripts/backfill_outlier50.py
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from brain import claude_api, context_builder
from brain.checkpoints import write_brain_file
from brain.prompts.outlier50 import OUTLIER50_USER_PROMPT
from clients import r2_client
from clients.moneyflows import MoneyFlowsClient
from storage import analyses, pdf_store
from storage.db import init_db, run_migrations

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


def run():
    init_db()
    run_migrations()
    mf = MoneyFlowsClient()

    print("Discovering historical Outlier 50 reports...")
    posts = []
    for page in range(2, 15):
        post = mf.get_outlier50_by_page(page)
        if not post:
            print(f"  page {page}: no post found — stopping discovery")
            break
        report_date = post["date"][:10]
        title = post.get("title", {}).get("rendered", "")
        print(f"  page {page}: {title} ({report_date})")
        posts.append((report_date, post))
        time.sleep(0.5)

    if not posts:
        print("No historical reports found.")
        return

    # Sort oldest first so checkpoint builds up correctly
    posts.sort(key=lambda x: x[0])
    print(f"\nFound {len(posts)} historical report(s). Processing oldest → newest...\n")

    # Clear the checkpoint so we build it fresh from history
    write_brain_file("OUTLIER50_CHECKPOINT.md", "# OUTLIER 50 CHECKPOINT\n\nNo data yet.\n")

    for i, (report_date, post) in enumerate(posts, 1):
        title = post.get("title", {}).get("rendered", "")
        print(f"[{i}/{len(posts)}] {title} ({report_date})")

        if pdf_store.pdf_already_archived("outlier50", report_date):
            print(f"       Already in archive — re-running analysis to build checkpoint...")

        pdf_url = mf.extract_pdf_url(post)
        if not pdf_url:
            print(f"       No PDF URL found — skipping")
            continue

        print(f"       Downloading PDF...")
        try:
            pdf_bytes = requests.get(
                pdf_url,
                headers={"User-Agent": _BROWSER_UA},
                timeout=60,
            ).content
            print(f"       {len(pdf_bytes):,} bytes")
        except Exception as e:
            print(f"       Download failed: {e} — skipping")
            continue

        print(f"       Uploading to R2...")
        try:
            year_month = report_date[:7].replace("-", "_")
            filename = f"outlier50_{year_month}.pdf"
            r2_url = r2_client.upload_from_url(pdf_url, filename)
            if not pdf_store.pdf_already_archived("outlier50", report_date):
                pdf_store.store_pdf("outlier50", report_date, pdf_url, filename, r2_url)
        except Exception as e:
            print(f"       R2 upload failed (continuing): {e}")

        print(f"       Running Claude analysis...")
        context = context_builder.build_context("outlier50")
        try:
            raw = claude_api.call_with_pdf(
                system=context,
                user=OUTLIER50_USER_PROMPT,
                pdf_bytes=pdf_bytes,
            )
            result = _parse_json(raw)
        except Exception as e:
            print(f"       Claude failed: {e} — skipping")
            continue

        write_brain_file("OUTLIER50_CHECKPOINT.md", result["checkpoint_update"])
        print(f"       Checkpoint updated.")

        if result.get("bmi") is not None:
            analyses.store_bmi(report_date, float(result["bmi"]))

        analyses.store_analysis(
            type="outlier50",
            report_date=report_date,
            summary=result.get("summary", ""),
            full_output=json.dumps(result),
        )

        print(f"       Done. Sleeping 5s before next report...")
        time.sleep(5)

    print(f"\nHistorical backfill complete. Now re-running current month (April 2026)...")
    # Re-run current month with full history as context
    from modules.outlier50_module import run as run_current
    run_current()

    print("\nBackfill complete. OUTLIER50_CHECKPOINT.md now has full history.")


if __name__ == "__main__":
    run()
