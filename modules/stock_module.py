import json
import re
from datetime import date

from brain import claude_api, context_builder
from brain.checkpoints import read_brain_file
from brain.prompts.stock_deep_dive import STOCK_DEEP_DIVE_PROMPT
from clients.quiverquant import get_all as quiver_get_all
from storage import analyses
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


def _format_quiver_data(data: dict) -> str:
    lines = []

    congress = sorted(data.get("congress_trades", []), key=lambda x: x.get("TransactionDate", ""), reverse=True)
    if congress:
        buys = [t for t in congress if "purchase" in (t.get("Transaction") or "").lower()]
        sells = [t for t in congress if "sale" in (t.get("Transaction") or "").lower()]
        excess_returns = [float(t["ExcessReturn"]) for t in congress if t.get("ExcessReturn") is not None]
        avg_excess = sum(excess_returns) / len(excess_returns) if excess_returns else None
        lines.append(f"CONGRESSIONAL TRADES ({len(congress)} total | {len(buys)} buys, {len(sells)} sells):")
        if avg_excess is not None:
            lines.append(f"  Avg excess return on prior trades: {avg_excess:+.1f}% vs SPY")
        for t in congress[:12]:
            chamber = "H" if t.get("House") == "House" else "S"
            party = (t.get("Party") or "?")[0]
            excess = f" | excess: {float(t['ExcessReturn']):+.1f}%" if t.get("ExcessReturn") is not None else ""
            lines.append(
                f"  {t.get('TransactionDate')} | [{chamber}/{party}] {t.get('Representative')} "
                f"| {t.get('Transaction')} {t.get('Range')}{excess}"
            )
    else:
        lines.append("Congressional trades: none on file.")

    contracts = data.get("gov_contracts_all", [])
    if contracts:
        recent = sorted(contracts, key=lambda x: x.get("Date", ""), reverse=True)[:5]
        total = sum(float(c.get("Amount", 0) or 0) for c in contracts)
        lines.append(f"\nGOV CONTRACTS ({len(contracts)} total, ${total:,.0f} cumulative):")
        for c in recent:
            lines.append(f"  {c.get('Date')} | {c.get('Agency')} | ${float(c.get('Amount', 0) or 0):,.0f} | {str(c.get('Description', ''))[:60]}")

    lobbying = data.get("lobbying", [])
    if lobbying:
        recent_lobby = sorted(lobbying, key=lambda x: x.get("Date", ""), reverse=True)[:5]
        total_lobby = sum(float(l.get("Amount", 0) or 0) for l in lobbying)
        lines.append(f"\nLOBBYING ({len(lobbying)} records, ${total_lobby:,.0f} total spend):")
        for l in recent_lobby[:3]:
            lines.append(f"  {l.get('Date')} | ${float(l.get('Amount', 0) or 0):,.0f} | {str(l.get('Issue', ''))[:60]}")

    offex = sorted(data.get("offexchange", []), key=lambda x: x.get("Date", ""), reverse=True)
    if offex:
        recent_offex = offex[:10]
        avg_dpi = sum(float(r.get("DPI", 0) or 0) for r in recent_offex) / len(recent_offex)
        lines.append(f"\nOFF-EXCHANGE SHORT VOLUME (last 10 days avg DPI: {avg_dpi:.1f}%):")
        for r in recent_offex[:5]:
            pct = round(100 * float(r.get("OTC_Short", 0) or 0) / max(float(r.get("OTC_Total", 1) or 1), 1), 1)
            lines.append(f"  {r.get('Date')} | OTC short: {pct}% of volume | DPI: {r.get('DPI')}")

    donors = data.get("corporate_donors", [])
    if donors:
        recent_donors = sorted(donors, key=lambda x: x.get("TransactionDate", ""), reverse=True)[:5]
        total_pac = sum(float(d.get("TransactionAmount", 0) or 0) for d in donors)
        lines.append(f"\nCORPORATE PAC DONATIONS ({len(donors)} records, ${total_pac:,.0f} total):")
        for d in recent_donors:
            lines.append(f"  {d.get('TransactionDate')} | ${float(d.get('TransactionAmount', 0) or 0):,.0f} → {str(d.get('CommitteeName', ''))[:50]}")

    return "\n".join(lines) if lines else "No Quiver Quant data available."


def _fetch_news(ticker: str) -> str:
    result = claude_api.call(
        system="You are a financial research assistant. Search the web for current information.",
        user=(
            f"Give me a brief research summary for {ticker} covering: "
            f"(1) recent news and catalysts, "
            f"(2) upcoming earnings date if known, "
            f"(3) recent analyst rating changes, "
            f"(4) current price and recent performance. "
            f"Be concise — 5-8 bullet points."
        ),
    )
    return result


def _build_watchlist_context(ticker: str) -> str:
    item = wl_store.get_watchlist_item(ticker)
    checkpoint = read_brain_file("OUTLIER50_CHECKPOINT.md")

    parts = []
    if item:
        parts.append(
            f"Watchlist entry: rank #{item.get('outlier_rank')}, "
            f"conviction={item.get('conviction')}, sector={item.get('sector')}\n"
            f"Notes: {item.get('notes', 'none')}"
        )
    else:
        parts.append(f"{ticker} is not currently on the watchlist.")

    # Pull the relevant section from the checkpoint
    pattern = rf"\*\*(?:Rank \d+: )?{re.escape(ticker)}\b[^*]*\*\*.*?(?=\n\*\*|\Z)"
    match = re.search(pattern, checkpoint, re.DOTALL)
    if match:
        parts.append(f"\nOutlier 50 checkpoint entry:\n{match.group(0)[:600]}")

    return "\n".join(parts)


def run(ticker: str) -> dict:
    """Run a full stock deep dive. Returns the parsed analysis dict."""
    init_db()
    ticker = ticker.upper()
    today = date.today().isoformat()

    print(f"[1/6] Loading context for {ticker}...")
    watchlist_context = _build_watchlist_context(ticker)
    print(f"       watchlist context: {len(watchlist_context)} chars")

    print("[2/6] Fetching Quiver Quant data...")
    try:
        quiver_data = quiver_get_all(ticker)
        congress_data = _format_quiver_data(quiver_data)
        counts = {k: len(v) for k, v in quiver_data.items() if isinstance(v, list)}
        print(f"       {counts}")
    except Exception as e:
        congress_data = f"Quiver Quant unavailable: {e}"
        print(f"       WARNING: {e}")

    print("[3/6] Fetching news and analyst data (web search)...")
    news_data = _fetch_news(ticker)
    print(f"       {len(news_data)} chars")

    print("[4/6] Running Claude deep dive analysis...")
    context = context_builder.build_context("stock_deep_dive")
    user_prompt = STOCK_DEEP_DIVE_PROMPT.format(
        ticker=ticker,
        date=today,
        congress_data=congress_data,
        news_data=news_data,
        watchlist_context=watchlist_context,
    )
    raw = claude_api.call(system=context, user=user_prompt)
    result = _parse_json(raw)
    print("       Done.")

    print("[5/6] Storing analysis...")
    analysis_id = analyses.store_analysis(
        type="stock_deep_dive",
        ticker=ticker,
        report_date=today,
        summary=result.get("summary", ""),
        full_output=json.dumps(result),
    )

    print("[6/6] Posting to Slack...")
    from clients.slack_client import send_to_main
    from slack.formatter import format_report
    from storage.analyses import update_slack_ts

    slack_report = result.get("slack_report", "")
    blocks = format_report(slack_report, header=f"Deep Dive: {ticker} — {today}")
    ts = send_to_main(text=f"Deep dive: {ticker}", blocks=blocks)
    update_slack_ts(analysis_id, ts)
    print(f"       posted (ts={ts})")

    print("\n" + "=" * 64)
    print(f"DEEP DIVE: {ticker} — {today}")
    print("=" * 64)
    print(slack_report)
    print("=" * 64)

    return result


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "MU"
    run(ticker)
