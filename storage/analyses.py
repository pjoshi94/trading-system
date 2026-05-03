from storage.db import get_connection


def store_analysis(
    type: str,
    report_date: str,
    summary: str,
    full_output: str = None,
    ticker: str = None,
    slack_ts: str = None,
    slack_summary: str = None,
    full_analysis: str = None,
) -> int:
    # full_analysis is canonical; full_output kept for backward compat
    if full_analysis and not full_output:
        full_output = full_analysis
    if not full_output:
        full_output = ""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO analyses
                (type, ticker, report_date, summary, full_output, slack_ts, slack_summary, full_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (type, ticker, report_date, summary, full_output, slack_ts, slack_summary, full_analysis),
        )
        return cur.lastrowid


def get_latest_analysis(type: str, ticker: str = None) -> dict | None:
    with get_connection() as conn:
        if ticker:
            row = conn.execute(
                "SELECT * FROM analyses WHERE type = ? AND ticker = ? ORDER BY created_at DESC LIMIT 1",
                (type, ticker),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM analyses WHERE type = ? ORDER BY created_at DESC LIMIT 1",
                (type,),
            ).fetchone()
        return dict(row) if row else None


def get_analyses(type: str, limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM analyses WHERE type = ? ORDER BY created_at DESC LIMIT ?",
            (type, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_by_slack_ts(slack_ts: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE slack_ts = ? ORDER BY id DESC LIMIT 1",
            (slack_ts,),
        ).fetchone()
        return dict(row) if row else None


def get_full_analysis(slack_ts: str) -> str | None:
    row = get_by_slack_ts(slack_ts)
    if not row:
        return None
    return row.get("full_analysis") or row.get("full_output")


def update_slack_ts(analysis_id: int, slack_ts: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE analyses SET slack_ts = ? WHERE id = ?",
            (slack_ts, analysis_id),
        )


# ------------------------------------------------------------------
# BMI history
# ------------------------------------------------------------------

def store_bmi(date: str, bmi_value: float, source: str = "weekly_flows"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO bmi_history (date, bmi_value, source) VALUES (?, ?, ?)",
            (date, bmi_value, source),
        )


def get_bmi_history(weeks: int = 8) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM bmi_history ORDER BY date DESC LIMIT ?",
            (weeks,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_bmi() -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM bmi_history ORDER BY date DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
