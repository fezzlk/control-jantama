import sqlite3
from pathlib import Path

from control_jantama.storage.replay_urls import insert_replay_url


def test_insert_replay_url_skips_duplicate_url(tmp_path: Path):
    db_path = tmp_path / "replay_urls.sqlite3"
    url = "https://game.mahjongsoul.com/?paipu=abc"

    first_id = insert_replay_url(db_path, url=url, row_index=0, success=True)
    second_id = insert_replay_url(db_path, url=url, row_index=1, success=True)

    assert first_id is not None
    assert second_id is None

    connection = sqlite3.connect(db_path)
    try:
        (count,) = connection.execute("SELECT COUNT(*) FROM replay_urls").fetchone()
    finally:
        connection.close()
    assert count == 1
