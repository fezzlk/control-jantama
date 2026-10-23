from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS replay_urls (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT NOT NULL,
    row_index    INTEGER NOT NULL,
    success      INTEGER NOT NULL,
    retrieved_at TEXT NOT NULL,
    match_type   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_replay_urls_url ON replay_urls(url);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(_SCHEMA)
    _ensure_match_type_column(connection)
    return connection


def _ensure_match_type_column(connection: sqlite3.Connection) -> None:
    """既存DB（match_type列が無いバージョンで作成済み）へ列を追加する。

    _SCHEMAのCREATE TABLE IF NOT EXISTSは新規DBにしか列を反映しないため、
    2026-09-21以前に作成済みのDBを使い続けられるよう明示的に移行する。
    """
    columns = {row[1] for row in connection.execute("PRAGMA table_info(replay_urls)")}
    if "match_type" not in columns:
        connection.execute("ALTER TABLE replay_urls ADD COLUMN match_type TEXT")
        connection.commit()
