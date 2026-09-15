from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from control_jantama.storage.db import get_connection


def insert_replay_url(db_path: Path, url: str, row_index: int, success: bool = True) -> int | None:
    """URLをSQLiteへ保存する。

    urlにUNIQUE制約があるため、既に記録済みのURLはINSERT OR IGNOREで無視され、
    その場合はNoneを返す（仮想リストの要素再利用により同じ行を重複取得しても、
    DBレベルで安全に弾くための設計）。
    """
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO replay_urls (url, row_index, success, retrieved_at) VALUES (?, ?, ?, ?)",
            (url, row_index, int(success), datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
        return int(cursor.lastrowid)
    finally:
        connection.close()
