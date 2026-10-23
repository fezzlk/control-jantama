from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from control_jantama.storage.db import get_connection


def insert_replay_url(
    db_path: Path,
    url: str,
    row_index: int,
    success: bool = True,
    match_type: str | None = None,
) -> int | None:
    """URLをSQLiteへ保存する。

    urlにUNIQUE制約があるため、既に記録済みのURLはINSERT OR IGNOREで無視され、
    その場合はNoneを返す（仮想リストの要素再利用により同じ行を重複取得しても、
    DBレベルで安全に弾くための設計）。

    match_type: 「段位戦」「友人戦」タブなど、取得元タブが分かっている場合に渡す
    （雀魂の一覧画面・牌譜URLのどちらにもこの情報は含まれていないため、タブを
    分けて実行することでしか判定できない）。既に記録済みのURLでmatch_typeが
    未設定(NULL)の場合は、重複扱いのままmatch_typeだけ後から埋める。一度別の
    値が入ったmatch_typeを上書きすることはない。
    """
    connection = get_connection(db_path)
    try:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO replay_urls (url, row_index, success, retrieved_at, match_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (url, row_index, int(success), datetime.now(timezone.utc).isoformat(), match_type),
        )
        if cursor.rowcount == 0:
            if match_type is not None:
                connection.execute(
                    "UPDATE replay_urls SET match_type = ? WHERE url = ? AND match_type IS NULL",
                    (match_type, url),
                )
            connection.commit()
            return None
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()
