from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import BrowserContext, Page, sync_playwright

from control_jantama.config import settings


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
