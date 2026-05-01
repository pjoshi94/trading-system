from brain.checkpoints import read_brain_file
from brain.prompts.system_context import SYSTEM_CONTEXT

_EXTRAS: dict[str, list[str]] = {
    "outlier50":       ["OUTLIER50_CHECKPOINT.md"],
    "weekly_flows":    ["WEEKLY_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
    "daily_check":     ["MARKET_CONDITIONS.md", "WEEKLY_CHECKPOINT.md"],
    "stock_deep_dive": ["OUTLIER50_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
    "post_earnings":   ["OUTLIER50_CHECKPOINT.md", "MARKET_CONDITIONS.md"],
}


def build_context(module_type: str) -> str:
    parts = [
        SYSTEM_CONTEXT,
        read_brain_file("TRADING_BRAIN.md"),
    ]
    for filename in _EXTRAS.get(module_type, []):
        parts.append(read_brain_file(filename))
    return "\n\n---\n\n".join(parts)
