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
