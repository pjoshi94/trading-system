import json
import re
from datetime import date

from brain import claude_api
from brain.checkpoints import read_brain_file, write_brain_file
from brain.prompts.position_parser import POSITION_PARSER_PROMPT
from storage import positions as pos_store
from storage.db import init_db


def _parse_json(text: str) -> dict:
    # Try fenced code block first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Walk string to find the first balanced {} block (handles extra text after JSON)
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Claude response")
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("Could not parse JSON from Claude response")


def _positions_context(positions: list) -> str:
    if not positions:
        return "No open positions."
    lines = []
    for p in positions:
        lines.append(
            f"- {p['ticker']}: {p['shares']} shares @ ${p['entry_price']:.2f} "
            f"(entered {p['entry_date']}, stop ${p['stop_loss']:.2f})"
        )
    return "\n".join(lines)


def _refresh_brain_positions(positions: list):
    """Rebuild the ## Open Positions section of TRADING_BRAIN.md from current DB state."""
    brain = read_brain_file("TRADING_BRAIN.md")

    if not positions:
        new_section = "## Open Positions\n\nNo open positions.\n"
    else:
        rows = [
            "| Ticker | Shares | Entry | Date | Stop | Target |",
            "|--------|--------|-------|------|------|--------|",
        ]
        for p in positions:
            target_low = round(p["entry_price"] * 1.20, 2)
            target_high = round(p["entry_price"] * 1.25, 2)
            rows.append(
                f"| {p['ticker']} | {p['shares']} | ${p['entry_price']:.2f} | "
                f"{p['entry_date']} | ${p['stop_loss']:.2f} | "
                f"${target_low:.2f}–${target_high:.2f} |"
            )
        new_section = "## Open Positions\n\n" + "\n".join(rows) + "\n"

    updated = re.sub(
        r"## Open Positions\n.*?(?=\n## |\Z)",
        new_section,
        brain,
        flags=re.DOTALL,
    )
    write_brain_file("TRADING_BRAIN.md", updated)


def parse_intent(message: str) -> dict:
    """Call Claude to parse a natural language position command."""
    positions = pos_store.get_open_positions()
    context = _positions_context(positions)
    prompt = POSITION_PARSER_PROMPT.format(
        message=message,
        positions_context=context,
    )
    raw = claude_api.call(
        system="You are a JSON parser. Return only valid JSON.",
        user=prompt,
    )
    return _parse_json(raw)


def _open_position(parsed: dict, today: str) -> str:
    ticker = parsed["ticker"]
    shares = parsed["shares"]
    price = parsed["price"]
    stop = round(price * 0.92, 2)
    target = round(price * 1.20, 2)

    pos_store.add_position(
        ticker=ticker,
        entry_price=price,
        entry_date=today,
        shares=shares,
        stop_loss=stop,
        profit_target=target,
    )

    positions = pos_store.get_open_positions()
    _refresh_brain_positions(positions)

    target_high = round(price * 1.25, 2)
    return (
        f":white_check_mark: Position opened: *{ticker}* — {shares} shares @ ${price:.2f} ({today})\n"
        f"Stop loss: *${stop:.2f}* (8% below entry — set this in Fidelity now)\n"
        f"Target: *${target:.2f} – ${target_high:.2f}* (+20–25%)\n"
        f"TRADING_BRAIN.md updated."
    )


def _close_position(parsed: dict, today: str) -> str:
    ticker = parsed["ticker"]
    exit_price = parsed["price"]

    pos = pos_store.get_open_position_by_ticker(ticker)
    if not pos:
        return f":x: No open position found for *{ticker}*."

    pnl = (exit_price - pos["entry_price"]) * pos["shares"]
    pnl_pct = ((exit_price - pos["entry_price"]) / pos["entry_price"]) * 100
    days_held = (date.fromisoformat(today) - date.fromisoformat(pos["entry_date"])).days

    exit_reason = "profit_target" if pnl_pct >= 18 else ("stop_loss" if pnl_pct <= -7 else "manual_exit")
    pos_store.close_position(pos["id"], exit_price, today, exit_reason)

    positions = pos_store.get_open_positions()
    _refresh_brain_positions(positions)

    sign = "+" if pnl >= 0 else ""
    return (
        f":white_check_mark: Position closed: *{ticker}* — {pos['shares']} shares @ ${exit_price:.2f}\n"
        f"P&L: *{sign}${pnl:.0f} ({sign}{pnl_pct:.1f}%)* over {days_held} days\n"
        f"TRADING_BRAIN.md updated."
    )


def _update_stop(parsed: dict) -> str:
    ticker = parsed["ticker"]
    new_stop = parsed["new_stop"]

    pos = pos_store.get_open_position_by_ticker(ticker)
    if not pos:
        return f":x: No open position found for *{ticker}*."

    current_stop = pos["stop_loss"]
    if new_stop < current_stop:
        return (
            f":x: Cannot lower stop loss. Current stop is ${current_stop:.2f}. "
            f"Stops can only move up."
        )
    if new_stop == current_stop:
        return f"Stop for *{ticker}* is already ${current_stop:.2f} — no change needed."

    pos_store.update_stop_loss(pos["id"], new_stop)

    positions = pos_store.get_open_positions()
    _refresh_brain_positions(positions)

    return (
        f":white_check_mark: Stop updated: *{ticker}* → *${new_stop:.2f}* (was ${current_stop:.2f})\n"
        f"Update this in Fidelity too."
    )


def _correct_position(parsed: dict, today: str) -> str:
    ticker = parsed["ticker"]
    pos = pos_store.get_open_position_by_ticker(ticker)
    if not pos:
        return f":x: No open position found for *{ticker}*."

    updates = {}
    if parsed.get("shares") is not None:
        updates["shares"] = parsed["shares"]
    if parsed.get("price") is not None:
        updates["entry_price"] = parsed["price"]
        updates["stop_loss"] = round(parsed["price"] * 0.92, 2)
        updates["profit_target"] = round(parsed["price"] * 1.20, 2)

    if not updates:
        return f":x: Nothing to correct — no new shares or price provided."

    pos_store.update_position(pos["id"], **updates)

    positions = pos_store.get_open_positions()
    _refresh_brain_positions(positions)

    changes = []
    if "shares" in updates:
        changes.append(f"shares: {pos['shares']} → {updates['shares']}")
    if "entry_price" in updates:
        changes.append(f"entry: ${pos['entry_price']:.2f} → ${updates['entry_price']:.2f}")
        changes.append(f"stop: ${pos['stop_loss']:.2f} → ${updates['stop_loss']:.2f}")

    return (
        f":white_check_mark: Position corrected: *{ticker}*\n"
        + "\n".join(f"• {c}" for c in changes)
        + "\nTRADING_BRAIN.md updated."
    )


def handle_position_command(message: str) -> str:
    """
    Parse and execute a natural language position command.
    Returns a Slack-formatted reply string.
    """
    init_db()
    today = date.today().isoformat()

    try:
        parsed = parse_intent(message)
    except Exception as e:
        return f":x: Could not parse that position command: {e}"

    intent = parsed.get("intent", "unclear")
    confidence = parsed.get("confidence", "low")
    missing = parsed.get("missing_fields", [])

    if intent == "unclear" or confidence == "low":
        if missing:
            missing_str = " and ".join(missing)
            ticker = parsed.get("ticker") or "the ticker"
            return (
                f":question: Got it, but I need: *{missing_str}*.\n"
                f"Try: \"I bought 43 shares of {ticker} at $73.25\""
            )
        return (
            ":question: I couldn't tell what position action you meant. Try:\n"
            "• `I bought 43 shares of FTI at $73.25`\n"
            "• `I sold FTI at $91.50`\n"
            "• `Update my FTI stop to $69.00`"
        )

    if intent == "open_position":
        return _open_position(parsed, today)
    elif intent == "close_position":
        return _close_position(parsed, today)
    elif intent == "update_stop":
        return _update_stop(parsed)
    elif intent == "correct_position":
        return _correct_position(parsed, today)

    return ":question: Unrecognized intent. Try `@super-trader help` for commands."
