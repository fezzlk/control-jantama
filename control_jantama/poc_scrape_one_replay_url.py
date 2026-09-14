"""最小PoC: 雀魂の牌譜一覧の先頭1行から共有URLを1件取得しSQLiteへ保存する。

対象外（意図的な先送り）: スクロール、複数行、重複排除、宣言的workflow、
OCR、画像LLMエスカレーション、Docker化。詳細はREADMEを参照。

事前条件: assets/templates/ 配下に共有アイコン・ダイアログ目印のテンプレート画像が
用意されていること（scripts/capture_reference_screenshot.py で手動作成）。
"""

from __future__ import annotations

import sys
from urllib.parse import urlparse

from control_jantama.action.clipboard import read_clipboard_text
from control_jantama.browser import get_or_create_page, launch_context, wait_for_human_navigation
from control_jantama.config import settings
from control_jantama.perception.template_match import decode_image, find_template, load_template
from control_jantama.storage.replay_urls import insert_replay_url

ROW_INDEX = 0  # このPoCはスクロールなし・先頭行のみを対象とする


def is_valid_replay_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    allowlist = settings.url_host_allowlist_entries
    if not allowlist:
        return True
    return any(entry in parsed.netloc for entry in allowlist)


def fail(message: str) -> None:
    print(f"FAILURE: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    with launch_context() as context:
        page = get_or_create_page(context)

        if settings.start_url:
            page.goto(settings.start_url)

        wait_for_human_navigation(
            "ブラウザが開きました。手動で雀魂にログインし、牌譜一覧画面を表示したら Enter を押してください。"
        )

        share_icon_template = load_template(settings.template_path(settings.share_icon_template))

        screenshot = decode_image(page.screenshot())
        match = find_template(screenshot, share_icon_template, threshold=settings.match_threshold)
        if match is None:
            fail("共有アイコンが見つかりませんでした（未知画面の可能性）。処理を中止します。")
            return

        click_x, click_y = match.center
        page.mouse.click(click_x, click_y)

        dialog_marker_template = load_template(settings.template_path(settings.dialog_marker_template))
        dialog_appeared = False
        elapsed_ms = 0
        poll_interval_ms = 500
        timeout_ms = int(settings.dialog_appear_timeout_seconds * 1000)
        while elapsed_ms <= timeout_ms:
            page.wait_for_timeout(poll_interval_ms)
            elapsed_ms += poll_interval_ms
            retry_screenshot = decode_image(page.screenshot())
            if find_template(retry_screenshot, dialog_marker_template, threshold=settings.match_threshold):
                dialog_appeared = True
                break

        if not dialog_appeared:
            fail("共有アイコンをクリックしましたが、共有ダイアログが表示されませんでした。")
            return

        if settings.copy_button_template:
            copy_button_template = load_template(settings.template_path(settings.copy_button_template))
            latest_screenshot = decode_image(page.screenshot())
            copy_match = find_template(latest_screenshot, copy_button_template, threshold=settings.match_threshold)
            if copy_match is None:
                fail("コピーボタンが見つかりませんでした。")
                return
            copy_x, copy_y = copy_match.center
            page.mouse.click(copy_x, copy_y)

        url = read_clipboard_text(page)

        if not is_valid_replay_url(url):
            fail(f"クリップボードの内容が有効なURLとして検証できませんでした: {url!r}")
            return

        row_id = insert_replay_url(settings.db_path, url=url, row_index=ROW_INDEX, success=True)

        page.keyboard.press("Escape")

        print(f"SUCCESS: retrieved {url}, saved to {settings.db_path} (row id {row_id})")


if __name__ == "__main__":
    main()
