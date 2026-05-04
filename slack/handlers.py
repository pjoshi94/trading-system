import re
import traceback
from datetime import date, datetime, timedelta

from brain import claude_api, context_builder
from brain.checkpoints import read_brain_file
from slack.formatter import format_report, format_watchlist, format_positions, format_bmi_history
from storage import analyses
from storage import positions as pos_store
from storage import watchlist as wl_store

_BUY_SELL_RE = re.compile(
    r"\b(bought|i bought|just bought|picked up|entered|got filled on|"
    r"sold|i sold|just sold|exited|closed my|closed out)\b",
    re.IGNORECASE,
)
# Stop update: action word + "stop" + dollar price all in same message
_STOP_UPDATE_RE = re.compile(
    r"\b(update|raise|move|set|tighten)\b.{0,40}\bstop\b.*\$\d",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def is_thread_keyword(text: str) -> bool:
    """Return True if text is a recognized thread keyword (no bot mention needed)."""
    clean = _clean(text).lower()
    return (
        clean in ("expand", "deep dive")
        or re.match(r"^why [a-z]+$", clean) is not None
    )


def route(text: str, say, thread_ts: str = None):
    clean = _clean(text).lower()
    kwargs = {"thread_ts": thread_ts} if thread_ts else {}

    # ── Thread keywords (work from any thread reply) ──────────────────────
    if clean == "expand" and thread_ts:
        _handle_expand(say, thread_ts, kwargs)
        return

    if clean == "deep dive" and thread_ts:
        _handle_deep_dive(say, thread_ts, kwargs)
        return

    m = re.match(r"^why ([a-z]+)$", clean)
    if m and thread_ts:
        _handle_why(m.group(1).upper(), say, thread_ts, kwargs)
        return

    # ── Scheduled module triggers ─────────────────────────────────────────
    if clean == "outlier50":
        say("Running Outlier 50 analysis — this takes ~60 seconds...", **kwargs)
        try:
            from modules.outlier50_module import run
            run()
        except Exception as e:
            print(f"[ERROR] outlier50 failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            say(f"Outlier 50 failed: {e}", **kwargs)

    elif clean == "weekly":
        say("Running Weekly Flows analysis — this takes ~60 seconds...", **kwargs)
        try:
            from modules.weekly_module import run
            run()
        except Exception as e:
            print(f"[ERROR] weekly failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            say(f"Weekly Flows failed: {e}", **kwargs)

    elif clean == "daily":
        say("Running nightly check — this takes ~60 seconds...", **kwargs)
        try:
            from modules.daily_module import run
            run()
        except Exception as e:
            print(f"[ERROR] daily failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            say(f"Nightly check failed: {e}", **kwargs)

    # ── Stock commands ────────────────────────────────────────────────────
    elif re.match(r"^analyze [a-z]+$", clean):
        ticker = clean.split(" ", 1)[1].upper()
        _handle_analyze(ticker, say, kwargs)

    # ── Watchlist management ──────────────────────────────────────────────
    elif re.match(r"^watchlist add [a-z]+$", clean):
        ticker = clean.split()[-1].upper()
        _handle_watchlist_add(ticker, say, kwargs)

    elif re.match(r"^earnings set [a-z]+ \d{4}-\d{2}-\d{2}$", clean):
        parts = clean.split()
        ticker = parts[2].upper()
        earnings_date = parts[3]
        _handle_earnings_set(ticker, earnings_date, say, kwargs)

    # ── DB read commands ──────────────────────────────────────────────────
    elif clean == "positions":
        rows = pos_store.get_open_positions()
        blocks = format_positions(rows)
        say(text="Open positions", blocks=blocks, **kwargs)

    elif clean == "watchlist":
        items = wl_store.get_watchlist()
        blocks = format_watchlist(items)
        say(text="Watchlist", blocks=blocks, **kwargs)

    elif clean == "bmi":
        history = analyses.get_bmi_history(8)
        blocks = format_bmi_history(history)
        say(text="BMI history", blocks=blocks, **kwargs)

    elif clean == "brain":
        brain = read_brain_file("TRADING_BRAIN.md")
        say(f"```{brain[:2900]}```", **kwargs)

    elif clean == "help":
        say(_help_text(), **kwargs)

    elif _is_position_command(_clean(text)):
        _handle_position_command(_clean(text), say, kwargs)

    else:
        _answer_question(_clean(text), say, thread_ts)


# ── Handler implementations ───────────────────────────────────────────────


def _handle_analyze(ticker: str, say, kwargs: dict):
    say(f"Running Tier 1 on *{ticker}* — ~30 seconds...", **kwargs)
    try:
        from modules.stock_module import run_tier1
        from clients.slack_client import send_to_main
        from storage.analyses import update_slack_ts

        result = run_tier1(ticker)
        blocks = format_report(result["slack_summary"], header=f"Tier 1: {ticker}")
        ts = send_to_main(
            text=f"Tier 1 complete for {ticker} — reply `deep dive` in this thread for full Quiver Quant analysis",
            blocks=blocks,
        )
        if result["analysis_id"]:
            update_slack_ts(result["analysis_id"], ts)
    except Exception as e:
        say(f"Tier 1 failed for {ticker}: {e}", **kwargs)


def _handle_expand(say, thread_ts: str, kwargs: dict):
    """Retrieve and post the full analysis stored for the parent message."""
    try:
        full = analyses.get_full_analysis(thread_ts)
        if not full:
            say("No stored analysis found for this thread.", **kwargs)
            return
        for i in range(0, len(full), 2900):
            say(full[i : i + 2900], **kwargs)
    except Exception as e:
        say(f"Expand failed: {e}", **kwargs)


def _handle_deep_dive(say, thread_ts: str, kwargs: dict):
    """
    `deep dive` in a thread: calls run_tier2 if this thread is a Tier 1 stock analysis.
    - type=stock_deep_dive  → run Tier 2 now
    - type=stock_deep_dive_tier2 → already done, use `expand`
    - anything else → not a stock analysis
    """
    try:
        row = analyses.get_by_slack_ts(thread_ts)
        if not row:
            say(
                "No analysis found for this thread. "
                "Use `@super-trader analyze TICKER` to start one.",
                **kwargs,
            )
            return

        analysis_type = row.get("type", "")

        if analysis_type == "stock_deep_dive_tier2":
            say(
                "Tier 2 has already been run for this stock. Reply `expand` to read it.",
                **kwargs,
            )
            return

        if analysis_type != "stock_deep_dive":
            say(
                "Deep dive is only available for stock analyses. "
                "Use `@super-trader analyze TICKER` to start one.",
                **kwargs,
            )
            return

        ticker = row.get("ticker")
        if not ticker:
            say("Could not determine ticker from this thread.", **kwargs)
            return

        # Extra guard: check if Tier 2 was already stored for this ticker
        existing_t2 = analyses.get_latest_analysis("stock_deep_dive_tier2", ticker=ticker)
        if existing_t2:
            say(
                f"Tier 2 has already been run for *{ticker}*. Reply `expand` to read it.",
                **kwargs,
            )
            return

        say(
            f"Running full Tier 2 on *{ticker}* (Quiver Quant + news) — ~60 seconds...",
            **kwargs,
        )
        from modules.stock_module import run_tier2
        from slack.formatter import format_report
        from storage.analyses import update_slack_ts

        result = run_tier2(ticker)
        blocks = format_report(
            result["slack_summary"],
            header=f"Tier 2 Deep Dive: {ticker} — {result['report_date']}",
        )
        say(
            text=f"Tier 2 complete for {ticker} — reply `expand` to read the full analysis",
            blocks=blocks,
            **kwargs,
        )
        if result["analysis_id"]:
            # Link to the parent thread so `expand` later finds Tier 2 content
            update_slack_ts(result["analysis_id"], thread_ts)

    except Exception as e:
        say(f"Deep dive failed: {e}", **kwargs)


def _handle_why(ticker: str, say, thread_ts: str, kwargs: dict):
    """Post the full analysis for a specific ticker — prefers Tier 2 if available."""
    try:
        row = (
            analyses.get_latest_analysis("stock_deep_dive_tier2", ticker=ticker)
            or analyses.get_latest_analysis("stock_deep_dive", ticker=ticker)
        )
        if not row:
            say(f"No stored analysis found for {ticker}.", **kwargs)
            return
        full = row.get("full_analysis") or row.get("full_output") or ""
        if not full:
            say(f"No detailed analysis stored for {ticker}.", **kwargs)
            return
        for i in range(0, len(full), 2900):
            say(full[i : i + 2900], **kwargs)
    except Exception as e:
        say(f"Why {ticker} lookup failed: {e}", **kwargs)


def _handle_watchlist_add(ticker: str, say, kwargs: dict):
    say(f"Adding *{ticker}* to watchlist and looking up earnings date...", **kwargs)
    try:
        today = date.today().isoformat()
        existing = wl_store.get_watchlist_item(ticker)
        if existing and existing.get("status") == "watching":
            say(f"*{ticker}* is already on the watchlist.", **kwargs)
            return

        import sqlite3
        try:
            wl_store.add_to_watchlist(ticker=ticker, added_date=today)
        except sqlite3.IntegrityError:
            wl_store.update_watchlist_item(ticker, status="watching")

        # Earnings lookup
        from clients.earnings import lookup_earnings_date, compute_earnings_block_dates
        result = lookup_earnings_date(ticker)

        if result["status"] in ("found", "low_confidence") and result["earnings_date"]:
            dates = compute_earnings_block_dates(result["earnings_date"])
            wl_store.update_earnings_dates(
                ticker=ticker,
                earnings_date=result["earnings_date"],
                pre_earnings_block_starts=dates["pre_earnings_block_starts"],
                entry_window_opens=dates["entry_window_opens"],
                earnings_confidence=result["confidence"],
            )
            confidence_tag = "" if result["confidence"] == "high" else " _(low confidence — verify)_"
            say(
                f":white_check_mark: *{ticker}* added to watchlist.\n"
                f"Earnings: {result['earnings_date']}{confidence_tag}\n"
                f"Entry block starts: {dates['pre_earnings_block_starts']} | "
                f"Entry window opens: {dates['entry_window_opens']}",
                **kwargs,
            )
        else:
            say(
                f":white_check_mark: *{ticker}* added to watchlist.\n"
                f":warning: Could not find earnings date — set manually with "
                f"`earnings set {ticker} YYYY-MM-DD`",
                **kwargs,
            )
    except Exception as e:
        say(f"Failed to add {ticker}: {e}", **kwargs)


def _handle_earnings_set(ticker: str, earnings_date: str, say, kwargs: dict):
    try:
        # Validate date format and that it's in the future
        dt = datetime.strptime(earnings_date, "%Y-%m-%d").date()
        if dt <= date.today():
            say(f":x: {earnings_date} is in the past. Provide a future date.", **kwargs)
            return

        item = wl_store.get_watchlist_item(ticker)
        if not item:
            say(f":x: *{ticker}* is not on the watchlist. Add it first with `watchlist add {ticker}`.", **kwargs)
            return

        from clients.earnings import compute_earnings_block_dates
        dates = compute_earnings_block_dates(earnings_date)
        wl_store.update_earnings_dates(
            ticker=ticker,
            earnings_date=earnings_date,
            pre_earnings_block_starts=dates["pre_earnings_block_starts"],
            entry_window_opens=dates["entry_window_opens"],
            earnings_confidence="high",
        )
        say(
            f":calendar: *{ticker}* earnings set to {earnings_date}.\n"
            f"Entry block starts: {dates['pre_earnings_block_starts']} | "
            f"Entry window opens: {dates['entry_window_opens']}",
            **kwargs,
        )
    except ValueError:
        say(f":x: Invalid date format. Use YYYY-MM-DD (e.g. `earnings set {ticker} 2026-05-15`).", **kwargs)
    except Exception as e:
        say(f"Failed to set earnings for {ticker}: {e}", **kwargs)


def _is_position_command(text: str) -> bool:
    """True if the message looks like a buy/sell/stop-update action, not a question."""
    if _STOP_UPDATE_RE.search(text):
        return True
    if not _BUY_SELL_RE.search(text):
        return False
    # Require a dollar price or a real ticker (2+ uppercase letters, not just "I")
    has_price = bool(re.search(r"\$\d+", text))
    has_ticker = bool(re.search(r"\b[A-Z]{2,5}\b", text))
    return has_price or has_ticker


def _handle_position_command(text: str, say, kwargs: dict):
    say(":hourglass_flowing_sand: Parsing position command...", **kwargs)
    try:
        from modules.position_module import handle_position_command
        reply = handle_position_command(text)
        say(reply, **kwargs)
    except Exception as e:
        say(f":x: Position command failed: {e}", **kwargs)


def _answer_question(question: str, say, thread_ts: str = None):
    print(f"[QA] question received: {question[:80]}")
    kwargs = {"thread_ts": thread_ts} if thread_ts else {}
    try:
        context = context_builder.build_context("qa")
        print(f"[QA] context built ({len(context)} chars), calling Claude...")
        response = claude_api.call_with_search(system=context, user=question)
        print(f"[QA] response received ({len(response)} chars)")
        for i in range(0, len(response), 2900):
            say(response[i : i + 2900], **kwargs)
    except Exception as e:
        print(f"[ERROR] _answer_question failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        err = str(e)
        if "Connection" in err or "connect" in err.lower() or "timeout" in err.lower():
            say("Network hiccup connecting to AI — please try again in a moment.", **kwargs)
        else:
            say(f"Sorry, something went wrong: {e}", **kwargs)


def _help_text() -> str:
    return (
        "*Commands:*\n"
        "• `@super-trader outlier50` — Run Outlier 50 analysis\n"
        "• `@super-trader weekly` — Run Weekly Flows analysis\n"
        "• `@super-trader daily` — Run nightly market check\n"
        "• `@super-trader analyze TICKER` — Quick Tier 1 filter\n"
        "• `@super-trader watchlist add TICKER` — Add ticker + auto earnings lookup\n"
        "• `@super-trader earnings set TICKER YYYY-MM-DD` — Set earnings date manually\n"
        "• `@super-trader positions` — Show open positions\n"
        "• `@super-trader watchlist` — Show current watchlist\n"
        "• `@super-trader bmi` — BMI history (last 8 weeks)\n"
        "• `@super-trader brain` — Dump current trading brain\n"
        "• `@super-trader help` — This message\n\n"
        "*Position tracking (natural language):*\n"
        "• `I bought 43 shares of FTI at $73.25`\n"
        "• `I sold FTI at $91.50`\n"
        "• `Update my FTI stop to $69.00`\n"
        "• `Correct my FTI entry — it was 40 shares not 43`\n\n"
        "*Thread keywords (reply in any analysis thread):*\n"
        "• `expand` or `deep dive` — Full stored analysis\n"
        "• `why TICKER` — Full analysis for a specific ticker\n\n"
        "Any other message → answered from brain context."
    )
