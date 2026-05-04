from datetime import date

from brain.checkpoints import read_brain_file
from brain.prompts.system_context import SYSTEM_CONTEXT

_EXTRAS: dict[str, list[str]] = {
    "outlier50":       ["OUTLIER50_CHECKPOINT.md"],
    "weekly_flows":    ["WEEKLY_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
    "daily_check":     ["MARKET_CONDITIONS.md", "WEEKLY_CHECKPOINT.md"],
    "stock_deep_dive": ["OUTLIER50_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
    "post_earnings":   ["OUTLIER50_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
    # Full context for Q&A — includes all checkpoint files so the bot can
    # answer questions about any stock, position, or market condition
    "qa":              ["OUTLIER50_CHECKPOINT.md", "WEEKLY_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
}


def build_context(module_type: str) -> str:
    parts = [
        SYSTEM_CONTEXT,
        read_brain_file("TRADING_BRAIN.md"),
    ]
    for filename in _EXTRAS.get(module_type, []):
        parts.append(read_brain_file(filename))
    return "\n\n---\n\n".join(parts)


def inject_position_context(summary: str) -> str:
    """
    Append open-position context inline for any ticker mentioned in the summary.
    Adds: Entry $X | Stop $X (Y% away) | Days held: N
    """
    try:
        from storage.positions import get_open_positions
        positions = get_open_positions()
    except Exception:
        return summary

    if not positions:
        return summary

    lines = []
    for pos in positions:
        ticker = pos["ticker"]
        if ticker not in summary.upper():
            continue
        entry = pos.get("entry_price")
        stop = pos.get("stop_loss")
        entry_date = pos.get("entry_date", "")
        try:
            days = (date.today() - date.fromisoformat(entry_date)).days
        except Exception:
            days = "?"
        if entry and stop:
            stop_pct = abs(entry - stop) / entry * 100
            lines.append(
                f"*{ticker}:* Entry ${entry:.2f} | Stop ${stop:.2f} ({stop_pct:.1f}% away) | {days}d held"
            )

    if lines:
        return summary + "\n\n_Positions:_ " + " · ".join(lines)
    return summary
