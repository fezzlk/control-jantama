from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from control_jantama.storage.db import get_connection


def insert_replay_url(db_path: Path, url: str, row_index: int, success: bool = True) -> int:
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            "INSERT INTO replay_urls (url, row_index, success, retrieved_at) VALUES (?, ?, ?, ?)",
            (url, row_index, int(success), datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()
