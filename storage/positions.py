from storage.db import get_connection


def add_position(
    ticker: str,
    entry_price: float,
    entry_date: str,
    shares: int,
    stop_loss: float,
    profit_target: float,
    thesis: str = "",
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO positions
                (ticker, entry_price, entry_date, shares, stop_loss, profit_target, thesis)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, entry_price, entry_date, shares, stop_loss, profit_target, thesis),
        )
        return cur.lastrowid


def get_open_positions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM positions WHERE status = 'open' ORDER BY entry_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_position(position_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM positions WHERE id = ?", (position_id,)
        ).fetchone()
        return dict(row) if row else None


def close_position(position_id: int, exit_price: float, exit_date: str, exit_reason: str):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE positions
            SET status = 'closed', exit_price = ?, exit_date = ?, exit_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (exit_price, exit_date, exit_reason, position_id),
        )


def get_all_positions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM positions ORDER BY entry_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]
