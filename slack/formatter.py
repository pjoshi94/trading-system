_MAX_BLOCK_LEN = 2900  # Slack section text limit is 3000; keep buffer


def _split_text(text: str, max_len: int = _MAX_BLOCK_LEN) -> list[str]:
    """Split text into chunks that fit within Slack's block text limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


def _divider() -> dict:
    return {"type": "divider"}


def _header(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def format_report(text: str, header: str = None) -> list:
    """Convert a free-text report to Slack blocks."""
    blocks = []
    if header:
        blocks.append(_header(header))
    for chunk in _split_text(text):
        blocks.append(_section(chunk))
    return blocks


def format_watchlist(items: list) -> list:
    """Format the watchlist table as Slack blocks."""
    if not items:
        return [_section("Watchlist is empty.")]
    blocks = [_header("Watchlist")]
    rows = []
    for item in items:
        rank = item.get("outlier_rank") or "—"
        conviction = item.get("conviction") or "—"
        sector = item.get("sector") or "—"
        notes = (item.get("notes") or "")[:80]
        rows.append(f"*{item['ticker']}* — rank {rank} | {conviction} | {sector}\n_{notes}_")
    blocks.append(_section("\n\n".join(rows)))
    return blocks


def format_positions(positions: list) -> list:
    """Format open positions as Slack blocks."""
    open_pos = [p for p in positions if p.get("status") == "open"]
    if not open_pos:
        return [_section("No open positions.")]
    blocks = [_header("Open Positions")]
    rows = []
    for p in open_pos:
        rows.append(
            f"*{p['ticker']}* — {p['shares']} shares @ ${p['entry_price']:.2f} "
            f"(entered {p['entry_date']})\n"
            f"Stop: ${p['stop_loss']:.2f} | Target: ${p['profit_target']:.2f}"
        )
    blocks.append(_section("\n\n".join(rows)))
    return blocks


def format_bmi_history(history: list) -> list:
    """Format BMI history as a Slack block."""
    if not history:
        return [_section("No BMI data yet.")]
    rows = [f"*Date* — *BMI*"]
    for entry in history:
        rows.append(f"{entry['date']} — {entry['bmi_value']}%")
    return [_header("BMI History (last 8 weeks)"), _section("\n".join(rows))]
