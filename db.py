"""SQLite データベースの初期化とアクセスヘルパー。"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS x_posts (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS x_fetch_state (
    username TEXT PRIMARY KEY,
    since_id TEXT
);

CREATE TABLE IF NOT EXISTS market_data (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_date TEXT NOT NULL,
    comment TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_changes (
    ticker TEXT NOT NULL,
    market TEXT NOT NULL,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    pct_change REAL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, date)
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """既存DBに後から追加した列を反映する(CREATE TABLE IF NOT EXISTSでは列は追加されないため)。"""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(market_data)")}
    for column in ("open", "high", "low"):
        if column not in existing:
            conn.execute(f"ALTER TABLE market_data ADD COLUMN {column} REAL")


# --- x_posts / x_fetch_state ---

def get_since_id(username: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT since_id FROM x_fetch_state WHERE username = ?", (username,)
        ).fetchone()
        return row["since_id"] if row else None


def set_since_id(username: str, since_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO x_fetch_state (username, since_id) VALUES (?, ?)
            ON CONFLICT(username) DO UPDATE SET since_id = excluded.since_id
            """,
            (username, since_id),
        )


def insert_post(post_id: str, username: str, created_at: str, text: str, url: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO x_posts (id, username, created_at, text, url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (post_id, username, created_at, text, url, now_iso()),
        )


def get_recent_posts(days: int = 7):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM x_posts
            WHERE created_at >= datetime('now', ?)
            ORDER BY created_at DESC
            """,
            (f"-{days} days",),
        ).fetchall()


# --- market_data ---

def upsert_market_point(
    symbol: str,
    date: str,
    close: float,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO market_data (symbol, date, open, high, low, close, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, date) DO UPDATE SET
                open = excluded.open, high = excluded.high, low = excluded.low,
                close = excluded.close, fetched_at = excluded.fetched_at
            """,
            (symbol, date, open_, high, low, close, now_iso()),
        )


def get_recent_market(symbol: str, days: int = 30):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM market_data
            WHERE symbol = ? AND date >= date('now', ?)
            ORDER BY date ASC
            """,
            (symbol, f"-{days} days"),
        ).fetchall()


# --- analysis ---

def insert_analysis(analysis_date: str, comment: str, model: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis (analysis_date, comment, model, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (analysis_date, comment, model, now_iso()),
        )


def get_latest_analysis():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM analysis ORDER BY created_at DESC LIMIT 1"
        ).fetchone()


# --- stock_changes (銘柄別ヒートマップ用) ---

def upsert_stock_change(ticker: str, market: str, name: str, date: str, pct_change: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO stock_changes (ticker, market, name, date, pct_change, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                pct_change = excluded.pct_change, fetched_at = excluded.fetched_at
            """,
            (ticker, market, name, date, pct_change, now_iso()),
        )


def get_latest_stock_changes(market: str):
    """指定マーケットについて、DBに保存されている最新日付の全銘柄の変化率を返す。"""
    with get_connection() as conn:
        latest = conn.execute(
            "SELECT MAX(date) AS d FROM stock_changes WHERE market = ?", (market,)
        ).fetchone()
        if not latest or not latest["d"]:
            return []
        return conn.execute(
            "SELECT * FROM stock_changes WHERE market = ? AND date = ? ORDER BY ticker",
            (market, latest["d"]),
        ).fetchall()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
