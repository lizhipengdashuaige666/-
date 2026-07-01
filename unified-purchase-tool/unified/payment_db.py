"""SQLite database layer for payment tracking.

WAL mode, foreign keys, singleton connection, schema migration via PRAGMA user_version.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
_PRIMARY_DIR = Path(r"D:\采购工作\采购订单\已发")
_FALLBACK_DIR = _HERE / "data"

if _PRIMARY_DIR.exists():
    DB_DIR = _PRIMARY_DIR
else:
    DB_DIR = _FALLBACK_DIR

DB_PATH = DB_DIR / "payment_tracking.db"
_connection: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    global _connection
    if _connection is not None:
        return _connection

    DB_DIR.mkdir(parents=True, exist_ok=True)
    _connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    _connection.execute("PRAGMA journal_mode=WAL")
    _connection.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(_connection)
    _run_migrations(_connection)
    return _connection


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS payment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_no TEXT NOT NULL UNIQUE,
            supplier_name TEXT NOT NULL,
            amount REAL NOT NULL,
            apply_date TEXT NOT NULL,
            po_number TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT '待审批',
            notes TEXT DEFAULT '',
            created_time TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_time TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS payment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            operator TEXT DEFAULT '当前用户',
            timestamp TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            notes TEXT DEFAULT '',
            FOREIGN KEY (payment_id) REFERENCES payment_records(id)
        );

        CREATE TABLE IF NOT EXISTS payment_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            created_time TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (payment_id) REFERENCES payment_records(id)
        );

        CREATE INDEX IF NOT EXISTS idx_records_payment_no ON payment_records(payment_no);
        CREATE INDEX IF NOT EXISTS idx_records_supplier ON payment_records(supplier_name);
        CREATE INDEX IF NOT EXISTS idx_records_status ON payment_records(status);
        CREATE INDEX IF NOT EXISTS idx_records_apply_date ON payment_records(apply_date);
        CREATE INDEX IF NOT EXISTS idx_logs_payment_id ON payment_logs(payment_id);
        CREATE INDEX IF NOT EXISTS idx_attachments_payment_id ON payment_attachments(payment_id);
    """)


def _run_migrations(conn: sqlite3.Connection) -> None:
    cur = conn.execute("PRAGMA user_version")
    version = cur.fetchone()[0]
    if version < 1:
        conn.execute("PRAGMA user_version = 1")


def close_db() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
