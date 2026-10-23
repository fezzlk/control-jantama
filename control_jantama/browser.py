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


def scroll_by(
    page: Page,
    total_px: int,
    tick_px: int,
    tick_interval_ms: int,
    move_to: tuple[int, int] | None = None,
) -> None:
    """総量total_pxを、tick_pxずつの小刻みなホイールイベントに分けて送る。

    実機確認(2026-09-15): 雀魂側は1回の大きなwheelイベント（例: deltaY=600）を
    そのままの量では反映せず、ごく僅かしかスクロールしない。実際のマウスホイールの
    1ノッチに近い小さな量を連続で送ることで、意図した総量に近づける。

    move_to: Playwrightの仮想マウスカーソルはmouse.move/clickしない限り直前の位置に
    残り続けるため、明示的に指定しないと「直前に処理した行の共有アイコン」等の
    成り行きの座標でwheelイベントが発火してしまう。一覧本体の上で確実にスクロール
    させるため、呼び出し側から一覧中央あたりの座標を渡す。
    """
    if move_to is not None:
        page.mouse.move(*move_to)

    remaining = total_px
    while remaining > 0:
        delta = min(tick_px, remaining)
        page.mouse.wheel(0, delta)
        page.wait_for_timeout(tick_interval_ms)
        remaining -= delta


def drag_scroll_by(
    page: Page,
    total_px: int,
    origin: tuple[int, int],
    drag_step_px: int = 300,
    move_steps: int = 10,
    step_delay_ms: int = 15,
    between_drags_ms: int = 100,
    settle_before_release_ms: int = 150,
) -> None:
    """マウスドラッグ（押す→上へ動かす→離す）でスクロールする。

    wheelイベントの反映が不安定な画面向けの代替手段(2026-09-21、友人戦タブで
    wheelがランダムに効かない事象への対策として追加)。一覧上の何もない場所
    （共有アイコン等のボタンに重ならない座標）を起点に、タッチスワイプに近い
    押す→上へ動かす→離す、を繰り返す。1回のドラッグで画面外へ出ないよう
    drag_step_pxずつに分けて複数回に分けて実行する。

    実機確認(2026-09-21): 雀魂の一覧は慣性スクロール（離す直前の速度が乗って
    追加でスクロールし続ける）が入っているため、動かし終えた直後に離すと
    想定より大きく動いてしまう。離す前にsettle_before_release_msだけ同じ位置に
    留まり、速度をゼロに近づけてから離すことでこれを抑える。
    """
    origin_x, origin_y = origin
    remaining = total_px

    while remaining > 0:
        drag_px = min(drag_step_px, remaining)
        page.mouse.move(origin_x, origin_y)
        page.mouse.down()
        target_y = origin_y
        for step in range(1, move_steps + 1):
            target_y = origin_y - int(drag_px * step / move_steps)
            page.mouse.move(origin_x, target_y)
            page.wait_for_timeout(step_delay_ms)
        page.mouse.move(origin_x, target_y)
        page.wait_for_timeout(settle_before_release_ms)
        page.mouse.up()
        page.wait_for_timeout(between_drags_ms)
        remaining -= drag_px


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
