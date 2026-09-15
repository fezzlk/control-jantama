from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS replay_urls (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT NOT NULL,
    row_index    INTEGER NOT NULL,
    success      INTEGER NOT NULL,
    retrieved_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_replay_urls_url ON replay_urls(url);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(_SCHEMA)
    return connection
