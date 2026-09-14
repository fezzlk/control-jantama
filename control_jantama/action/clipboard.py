from __future__ import annotations

from playwright.sync_api import Page


def read_clipboard_text(page: Page, wait_ms: int = 200) -> str:
    """クリップボードのテキストを読む。

    直前のコピー操作が非同期の場合があるため、読む前に短く待つ。
    呼び出し側で context.grant_permissions(["clipboard-read", "clipboard-write"])
    が既に実行されている前提。
    """
    page.wait_for_timeout(wait_ms)
    return page.evaluate("navigator.clipboard.readText()")
