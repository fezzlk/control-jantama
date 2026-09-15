from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import BrowserContext, Page, sync_playwright

from control_jantama.config import settings
from control_jantama.perception.screen_diff import images_are_similar
from control_jantama.perception.template_match import decode_image


@contextmanager
def launch_context() -> Iterator[BrowserContext]:
    """雀魂操作用の永続ブラウザコンテキストを起動する。

    device_scale_factor=1 は必須: これが無いとRetinaディスプレイでの
    screenshot()の座標系とmouse.click()の座標系がずれ、
    テンプレートマッチングの結果をそのままクリック座標に使えなくなる。
    リファクタ時にも絶対に落とさないこと。
    """
    settings.user_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(settings.user_data_dir),
            headless=False,
            viewport={"width": settings.viewport_width, "height": settings.viewport_height},
            device_scale_factor=1,
        )
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        try:
            yield context
        finally:
            context.close()


def get_or_create_page(context: BrowserContext) -> Page:
    return context.pages[0] if context.pages else context.new_page()


def wait_for_human_navigation(prompt: str) -> None:
    print(prompt)
    input()


def wait_for_stable_screenshot(
    page: Page,
    poll_interval_ms: int,
    stable_checks: int,
    timeout_ms: int,
    threshold: float,
) -> bytes:
    """画面が変化しなくなるまで待ち、その時点のスクリーンショットを返す。

    雀魂の遅延ロード（古い牌譜が段階的にロードされる）完了を待つために使う。
    連続でstable_checks回`images_are_similar`が真になったら安定とみなす。
    タイムアウトした場合も、未知の停止状態を推測で埋めずにその時点の画面を返す
    （呼び出し側でスクロール前後の比較により end-of-list 判定を行う）。
    """
    latest = page.screenshot()
    consecutive_stable = 0
    elapsed_ms = 0

    while elapsed_ms <= timeout_ms:
        page.wait_for_timeout(poll_interval_ms)
        elapsed_ms += poll_interval_ms

        current = page.screenshot()
        if images_are_similar(decode_image(latest), decode_image(current), threshold=threshold):
            consecutive_stable += 1
            if consecutive_stable >= stable_checks:
                return current
        else:
            consecutive_stable = 0

        latest = current

    return latest
