from storage.db import get_connection


def store_pdf(
    type: str,
    report_date: str,
    original_url: str,
    filename: str,
    r2_url: str = None,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO pdf_archive (type, report_date, original_url, r2_url, filename)
            VALUES (?, ?, ?, ?, ?)
            """,
            (type, report_date, original_url, r2_url, filename),
        )
        return cur.lastrowid


def get_latest_pdf(type: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pdf_archive WHERE type = ? ORDER BY created_at DESC LIMIT 1",
            (type,),
        ).fetchone()
        return dict(row) if row else None


def pdf_already_archived(type: str, report_date: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM pdf_archive WHERE type = ? AND report_date = ?",
            (type, report_date),
        ).fetchone()
        return row is not None
