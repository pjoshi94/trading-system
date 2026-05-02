import re

from brain import claude_api, context_builder
from brain.checkpoints import read_brain_file
from slack.formatter import format_report, format_watchlist, format_positions, format_bmi_history
from storage import analyses
from storage import positions as pos_store
from storage import watchlist as wl_store


def _clean(text: str) -> str:
    """Strip bot mention and normalize whitespace."""
    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def route(text: str, say, thread_ts: str = None):
    """Parse the message and route to the correct handler."""
    clean = _clean(text).lower()
    kwargs = {"thread_ts": thread_ts} if thread_ts else {}

    if clean == "outlier50":
        say("Running Outlier 50 analysis — this takes ~60 seconds...", **kwargs)
        try:
            from modules.outlier50_module import run
            run()
        except Exception as e:
            say(f"Outlier 50 failed: {e}", **kwargs)

    elif clean == "weekly":
        say("Running Weekly Flows analysis — this takes ~60 seconds...", **kwargs)
        try:
            from modules.weekly_module import run
            run()
        except Exception as e:
            say(f"Weekly Flows failed: {e}", **kwargs)

    elif clean == "daily":
        say("Running nightly check — coming in Step 10.", **kwargs)

    elif re.match(r"^analyze [a-z]+$", clean):
        ticker = clean.split(" ", 1)[1].upper()
        say(f"Stock deep dive on *{ticker}* — coming in Step 11.", **kwargs)

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

    else:
        _answer_question(_clean(text), say, thread_ts)


def _answer_question(question: str, say, thread_ts: str = None):
    """Answer a free-form question using the full brain context."""
    kwargs = {"thread_ts": thread_ts} if thread_ts else {}
    try:
        context = context_builder.build_context("daily_check")
        response = claude_api.call(system=context, user=question)
        for i in range(0, len(response), 2900):
            say(response[i : i + 2900], **kwargs)
    except Exception as e:
        say(f"Sorry, something went wrong: {e}", **kwargs)


def _help_text() -> str:
    return (
        "*Commands:*\n"
        "• `@super-trader outlier50` — Run Outlier 50 analysis\n"
        "• `@super-trader weekly` — Run Weekly Flows analysis\n"
        "• `@super-trader daily` — Run nightly market check\n"
        "• `@super-trader analyze TICKER` — Stock deep dive\n"
        "• `@super-trader positions` — Show open positions\n"
        "• `@super-trader watchlist` — Show current watchlist\n"
        "• `@super-trader bmi` — BMI history (last 8 weeks)\n"
        "• `@super-trader brain` — Dump current trading brain\n"
        "• `@super-trader help` — This message\n\n"
        "Any other message → answered from brain context."
    )
