from storage.db import get_connection


def add_to_watchlist(
    ticker: str,
    added_date: str,
    outlier_rank: int = None,
    out20_count: int = None,
    map_score: float = None,
    sector: str = None,
    earnings_date: str = None,
    conviction: str = None,
    notes: str = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO watchlist
                (ticker, added_date, outlier_rank, out20_count, map_score,
                 sector, earnings_date, conviction, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, added_date, outlier_rank, out20_count, map_score,
             sector, earnings_date, conviction, notes),
        )
        return cur.lastrowid


def get_watchlist() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE status = 'watching' ORDER BY outlier_rank ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_watchlist_item(ticker: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM watchlist WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
        return dict(row) if row else None


def update_watchlist_item(ticker: str, **kwargs):
    if not kwargs:
        return
    kwargs["updated_at"] = "CURRENT_TIMESTAMP"
    # Build SET clause — updated_at uses a SQL function so handle it separately
    fields = {k: v for k, v in kwargs.items() if k != "updated_at"}
    set_parts = [f"{k} = ?" for k in fields] + ["updated_at = CURRENT_TIMESTAMP"]
    values = list(fields.values()) + [ticker.upper()]
    with get_connection() as conn:
        conn.execute(
            f"UPDATE watchlist SET {', '.join(set_parts)} WHERE ticker = ?",
            values,
        )


def remove_from_watchlist(ticker: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE watchlist SET status = 'removed', updated_at = CURRENT_TIMESTAMP WHERE ticker = ?",
            (ticker.upper(),),
        )


def update_earnings_dates(
    ticker: str,
    earnings_date: str,
    pre_earnings_block_starts: str = None,
    entry_window_opens: str = None,
    earnings_confidence: str = "high",
):
    """Set earnings-related date columns on a watchlist entry."""
    update_watchlist_item(
        ticker,
        earnings_date=earnings_date,
        pre_earnings_block_starts=pre_earnings_block_starts,
        entry_window_opens=entry_window_opens,
        earnings_confidence=earnings_confidence,
        deep_dive_queued=1,
    )


def get_entry_window_ready(today: str) -> list[dict]:
    """Return watchlist entries where entry_window_opens = today AND deep_dive_queued = 1."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE entry_window_opens = ? AND deep_dive_queued = 1 AND status = 'watching'",
            (today,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_watchlist_by_earnings_date(earnings_date: str) -> list[dict]:
    """Return active watchlist entries with a specific earnings_date."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE earnings_date = ? AND status = 'watching'",
            (earnings_date,),
        ).fetchall()
        return [dict(r) for r in rows]
