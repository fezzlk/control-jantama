"""headless Chromiumで雀魂のWebGL/Canvas描画が撮れるかを検証する（FEZ-190）。

headless=True（既定のGL）と headless=True + --use-gl=swiftshader の2通りで
雀魂を開き、画面が安定するまで待ってスクリーンショットを撮る。あわせて
WebGLのコンテキスト取得可否・レンダラー名と、画像が「真っ黒・単色でないか」を
数値で記録する。headed運用の参考画像（assets/screenshots/reference.png）が
あれば類似度も記録するが、参考画像は牌譜一覧画面なので、ログイン状態や
遷移先が違えば低い値になる。合否はスクリーンショットを目視して判断する。

既存の data/user_data_dir（実アカウントのログインセッション）は直接開かない。
--user-data-dir を省略すると空の一時プロファイルで起動する（ログイン画面まで）。
ログインセッションの引き継ぎも見たい場合は、data/user_data_dir をコピーした
ディレクトリを渡す（headed運用中のプロファイルと競合・変更しないため）。

    venv/bin/python -m scripts.verify_headless_rendering --output-dir <dir>
    venv/bin/python -m scripts.verify_headless_rendering --output-dir <dir> \
        --user-data-dir /tmp/copied_user_data_dir
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

from control_jantama.config import settings
from control_jantama.perception.template_match import decode_image, find_template, load_template

GAME_URL = "https://game.mahjongsoul.com/index.html"
REFERENCE_IMAGE = Path("assets/screenshots/reference.png")

MODES: dict[str, list[str]] = {
    "headless-default": [],
    "headless-swiftshader": ["--use-gl=swiftshader"],
}

WEBGL_PROBE_JS = """
() => {
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
  if (!gl) return {available: false};
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  return {
    available: true,
    version: gl.getParameter(gl.VERSION),
    renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
    canvases_on_page: document.querySelectorAll('canvas').length,
  };
}
"""

# 単色・真っ黒の判定に使う閾値。雀魂のロード後画面は背景イラスト・UIで
# 輝度のばらつきが大きいため、標準偏差が小さすぎる画像は描画失敗とみなす。
MIN_STDDEV = 8.0
MAX_DARK_RATIO = 0.95
DARK_LEVEL = 16


@dataclass(frozen=True)
class ImageStats:
    mean: float
    stddev: float
    dark_ratio: float
    distinct_colors: int

    @property
    def looks_rendered(self) -> bool:
        """真っ黒・単色でなければ「何かが描画されている」とみなす。"""
        return self.stddev >= MIN_STDDEV and self.dark_ratio <= MAX_DARK_RATIO


def image_stats(image: np.ndarray) -> ImageStats:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    quantized = (image // 16).reshape(-1, image.shape[2])
    return ImageStats(
        mean=float(gray.mean()),
        stddev=float(gray.std()),
        dark_ratio=float((gray < DARK_LEVEL).mean()),
        distinct_colors=int(len(np.unique(quantized, axis=0))),
    )


def similarity(a: np.ndarray, b: np.ndarray) -> float | None:
    """平均絶対差分による類似度（screen_diff.images_are_similar と同じ式）。"""
    if a.shape != b.shape:
        return None
    mean_abs_diff = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())
    return 1.0 - (mean_abs_diff / 255.0)


def template_scores(image: np.ndarray, templates_dir: Path) -> dict[str, float | None]:
    """テンプレート画像ごとの一致スコア（閾値0で最良値を取る）。無ければ空。"""
    scores: dict[str, float | None] = {}
    if not templates_dir.is_dir():
        return scores
    for path in sorted(templates_dir.glob("*.png")):
        match = find_template(image, load_template(path), threshold=0.0)
        scores[path.name] = match.score if match else None
    return scores


def wait_until_stable(page, timeout_ms: int, min_wait_ms: int, poll_ms: int = 1000,
                      stable_checks: int = 5) -> bytes:
    """ロード画面が落ち着くまで待つ。タイムアウト時はその時点の画面。

    ダウンロード中の進捗バーは画面のごく一部しか変わらないため、閾値を
    厳しく（0.9995）し、さらに min_wait_ms 経過までは安定と判定しない。
    """
    page.wait_for_timeout(min_wait_ms)
    latest = page.screenshot()
    stable = 0
    elapsed = min_wait_ms
    while elapsed < timeout_ms:
        page.wait_for_timeout(poll_ms)
        elapsed += poll_ms
        current = page.screenshot()
        value = similarity(decode_image(latest), decode_image(current))
        stable = stable + 1 if value is not None and value >= 0.9995 else 0
        latest = current
        if stable >= stable_checks:
            break
    return latest


def run_mode(playwright, mode: str, extra_args: list[str], user_data_dir: Path, output_dir: Path,
             timeout_ms: int, min_wait_ms: int) -> dict:
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=True,
        args=extra_args,
        viewport={"width": settings.viewport_width, "height": settings.viewport_height},
        device_scale_factor=1,
    )
    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(GAME_URL, wait_until="load", timeout=60_000)
        screenshot = wait_until_stable(page, timeout_ms, min_wait_ms)
        webgl = page.evaluate(WEBGL_PROBE_JS)
        user_agent = page.evaluate("() => navigator.userAgent")
    finally:
        context.close()

    path = output_dir / f"{mode}.png"
    path.write_bytes(screenshot)
    image = decode_image(screenshot)
    stats = image_stats(image)

    reference_similarity = None
    if REFERENCE_IMAGE.exists():
        reference_similarity = similarity(image, load_template(REFERENCE_IMAGE))

    return {
        "mode": mode,
        "args": extra_args,
        "screenshot": str(path),
        "webgl": webgl,
        "user_agent": user_agent,
        "stats": asdict(stats),
        "looks_rendered": stats.looks_rendered,
        "reference_similarity": reference_similarity,
        "template_scores": template_scores(image, settings.templates_dir),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--user-data-dir", type=Path, default=None,
                        help="省略時は空の一時プロファイル。data/user_data_dir は直接渡さず、コピーを渡す")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--min-wait-seconds", type=float, default=30.0,
                        help="ゲームデータのダウンロードを待つ最低時間")
    parser.add_argument("--modes", nargs="+", choices=sorted(MODES), default=list(MODES))
    args = parser.parse_args(argv)

    if args.user_data_dir and args.user_data_dir.resolve() == settings.user_data_dir.resolve():
        parser.error("data/user_data_dir は直接使わず、コピーしたディレクトリを渡してください")

    from playwright.sync_api import sync_playwright

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timeout_ms = int(args.timeout_seconds * 1000)
    min_wait_ms = int(args.min_wait_seconds * 1000)
    results = []
    with sync_playwright() as playwright:
        for mode in args.modes:
            if args.user_data_dir:
                results.append(run_mode(playwright, mode, MODES[mode], args.user_data_dir,
                                        args.output_dir, timeout_ms, min_wait_ms))
            else:
                with tempfile.TemporaryDirectory(prefix="cj-headless-") as tmp:
                    results.append(run_mode(playwright, mode, MODES[mode], Path(tmp),
                                            args.output_dir, timeout_ms, min_wait_ms))

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for result in results:
        webgl = result["webgl"]
        print(f"{result['mode']}: rendered={result['looks_rendered']} "
              f"webgl={webgl.get('available')} renderer={webgl.get('renderer')} "
              f"stddev={result['stats']['stddev']:.1f} screenshot={result['screenshot']}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
