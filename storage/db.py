import sqlite3
import os
from config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    entry_price REAL NOT NULL,
    entry_date TEXT NOT NULL,
    shares INTEGER NOT NULL,
    stop_loss REAL NOT NULL,
    profit_target REAL NOT NULL,
    thesis TEXT,
    status TEXT DEFAULT 'open',
    exit_price REAL,
    exit_date TEXT,
    exit_reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    added_date TEXT NOT NULL,
    outlier_rank INTEGER,
    out20_count INTEGER,
    map_score REAL,
    sector TEXT,
    earnings_date TEXT,
    entry_blocked_until TEXT,
    conviction TEXT,
    notes TEXT,
    status TEXT DEFAULT 'watching',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    ticker TEXT,
    report_date TEXT NOT NULL,
    summary TEXT NOT NULL,
    full_output TEXT NOT NULL,
    slack_ts TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bmi_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    bmi_value REAL NOT NULL,
    source TEXT DEFAULT 'weekly_flows',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pdf_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    report_date TEXT NOT NULL,
    original_url TEXT NOT NULL,
    r2_url TEXT,
    filename TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection() -> sqlite3.Connection:
    db_dir = os.path.dirname(settings.DATABASE_URL)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()


def run_migrations():
    """Add new columns to existing tables. Safe to run multiple times."""
    migrations = [
        "ALTER TABLE watchlist ADD COLUMN pre_earnings_block_starts TEXT",
        "ALTER TABLE watchlist ADD COLUMN entry_window_opens TEXT",
        "ALTER TABLE watchlist ADD COLUMN earnings_confidence TEXT",
        "ALTER TABLE watchlist ADD COLUMN deep_dive_queued INTEGER DEFAULT 0",
        "ALTER TABLE analyses ADD COLUMN slack_summary TEXT",
        "ALTER TABLE analyses ADD COLUMN full_analysis TEXT",
    ]
    conn = get_connection()
    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    conn.close()
    print("  Migrations: OK")
