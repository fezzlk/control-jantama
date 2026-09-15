"""雀魂の牌譜一覧をスクロールしながら、表示されている各行の共有URLを取得しSQLiteへ保存する。

対象外（意図的な先送り）: 宣言的workflow、中断・再開チェックポイント、
trainer（画面記録UI）、Docker/headless化。詳細はREADMEを参照。

事前条件: assets/templates/ 配下に共有アイコン・ダイアログ目印のテンプレート画像が
用意されていること（scripts/capture_reference_screenshot.py で手動作成）。
"""

from __future__ import annotations

import re
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import Page

from control_jantama.action.clipboard import read_clipboard_text
from control_jantama.browser import (
    get_or_create_page,
    launch_context,
    scroll_by,
    wait_for_human_navigation,
    wait_for_stable_screenshot,
)
from control_jantama.config import settings
from control_jantama.perception.screen_diff import images_are_similar
from control_jantama.perception.template_match import Match, decode_image, find_all_templates, find_template, load_template
from control_jantama.storage.replay_urls import insert_replay_url

# クリップボードは「雀魂牌譜:https://...」のように説明文付きでコピーされるため、
# 中に含まれるURL部分だけを抜き出す。
_URL_PATTERN = re.compile(r"https?://\S+")


def extract_url(text: str) -> str | None:
    match = _URL_PATTERN.search(text)
    return match.group(0) if match else None


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


def capture_row_url(
    page: Page,
    match: Match,
    dialog_marker_template,
    copy_button_template: str | None,
) -> str:
    """1行分: 共有アイコンをクリックしてダイアログを開き、URLをコピーして取得する。

    異常時は未知状態を推測で埋めず即座にfail()で終了する。
    """
    click_x, click_y = match.center
    page.mouse.click(click_x, click_y)

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

    if settings.copy_button_template:
        copy_button_template_image = load_template(settings.template_path(settings.copy_button_template))
        latest_screenshot = decode_image(page.screenshot())
        copy_match = find_template(latest_screenshot, copy_button_template_image, threshold=settings.match_threshold)
        if copy_match is None:
            fail("コピーボタンが見つかりませんでした。")
        copy_x, copy_y = copy_match.center
        page.mouse.click(copy_x, copy_y)

    clipboard_text = read_clipboard_text(page)
    url = extract_url(clipboard_text)

    if url is None or not is_valid_replay_url(url):
        fail(f"クリップボードの内容から有効なURLを抽出できませんでした: {clipboard_text!r}")

    page.keyboard.press("Escape")

    assert url is not None  # fail()はsys.exit()するため、ここに到達する時点でurlは非None
    return url


def run_capture_loop(page: Page) -> tuple[int, int, int, float]:
    """一覧内の各行を捕捉しつつスクロールし、末尾に到達するまで繰り返す。

    戻り値: (新規保存件数, 重複スキップ件数, スクロール回数, 合計処理時間[秒])
    """
    share_icon_template = load_template(settings.template_path(settings.share_icon_template))
    dialog_marker_template = load_template(settings.template_path(settings.dialog_marker_template))

    saved_count = 0
    duplicate_count = 0
    capture_order = 0
    scroll_count = 0
    loop_started_at = time.monotonic()

    while True:
        screenshot = decode_image(page.screenshot())
        matches = find_all_templates(
            screenshot,
            share_icon_template,
            threshold=settings.match_threshold,
            min_distance_px=settings.row_match_min_distance_px,
        )

        for match in matches:
            row_started_at = time.monotonic()
            url = capture_row_url(page, match, dialog_marker_template, settings.copy_button_template)
            row_id = insert_replay_url(settings.db_path, url=url, row_index=capture_order, success=True)
            row_elapsed_seconds = time.monotonic() - row_started_at
            capture_order += 1
            if row_id is None:
                duplicate_count += 1
                outcome = "duplicate"
            else:
                saved_count += 1
                outcome = "saved"
            print(f"row {capture_order}: {outcome} {url} ({row_elapsed_seconds:.1f}s)")

        if settings.max_scroll_steps is not None and scroll_count >= settings.max_scroll_steps:
            break

        before_scroll_screenshot = page.screenshot()
        scroll_by(
            page,
            total_px=settings.scroll_step_px,
            tick_px=settings.scroll_tick_px,
            tick_interval_ms=settings.scroll_tick_interval_ms,
            move_to=(settings.viewport_width // 2, settings.viewport_height // 2),
        )
        after_scroll_screenshot = wait_for_stable_screenshot(
            page,
            poll_interval_ms=settings.scroll_settle_poll_interval_ms,
            stable_checks=settings.scroll_settle_stable_checks,
            timeout_ms=int(settings.scroll_settle_timeout_seconds * 1000),
            threshold=settings.screen_similarity_threshold,
        )
        scroll_count += 1

        if images_are_similar(
            decode_image(before_scroll_screenshot),
            decode_image(after_scroll_screenshot),
            threshold=settings.screen_similarity_threshold,
        ):
            break

    elapsed_seconds = time.monotonic() - loop_started_at
    return saved_count, duplicate_count, scroll_count, elapsed_seconds


def main() -> None:
    with launch_context() as context:
        page = get_or_create_page(context)

        if settings.start_url:
            page.goto(settings.start_url)

        wait_for_human_navigation(
            "ブラウザが開きました。手動で雀魂にログインし、牌譜一覧画面を表示したら Enter を押してください。"
        )

        saved_count, duplicate_count, scroll_count, elapsed_seconds = run_capture_loop(page)

        total_rows = saved_count + duplicate_count
        avg_seconds_per_row = elapsed_seconds / total_rows if total_rows else 0.0

        print(
            f"SUCCESS: saved {saved_count} new url(s), skipped {duplicate_count} duplicate(s) "
            f"across {scroll_count} scroll step(s) in {elapsed_seconds:.1f}s "
            f"(avg {avg_seconds_per_row:.1f}s/row over {total_rows} row(s)), saved to {settings.db_path}"
        )


if __name__ == "__main__":
    main()
