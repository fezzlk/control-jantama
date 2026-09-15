import numpy as np

from control_jantama.perception.template_match import find_all_templates, find_template


def _checkerboard_patch(size: int = 20) -> np.ndarray:
    """内部にコントラストを持つテンプレート。

    単色ブロックはTM_CCOEFF_NORMEDでは分散ゼロになり相関係数が
    数値的に不安定（degenerate）になるため、テスト用には使わない。
    """
    pattern = np.indices((size, size)).sum(axis=0) % 2
    patch = (pattern * 255).astype(np.uint8)
    return np.stack([patch, patch, patch], axis=-1)


def _gradient_canvas(height: int = 200, width: int = 300) -> np.ndarray:
    y = np.linspace(0, 255, height, dtype=np.uint8)
    x = np.linspace(0, 255, width, dtype=np.uint8)
    gradient = (y[:, None].astype(np.uint16) + x[None, :].astype(np.uint16)) // 2
    gradient = gradient.astype(np.uint8)
    return np.stack([gradient, gradient, gradient], axis=-1)


def test_find_template_locates_embedded_patch():
    canvas = _gradient_canvas()
    patch = _checkerboard_patch()
    canvas[50:70, 100:120] = patch

    match = find_template(canvas, patch, threshold=0.9)

    assert match is not None
    assert match.x == 100
    assert match.y == 50


def test_find_template_returns_none_when_absent():
    canvas = _gradient_canvas()
    patch = _checkerboard_patch()

    match = find_template(canvas, patch, threshold=0.9)

    assert match is None


def test_find_all_templates_locates_multiple_rows_top_to_bottom():
    canvas = _gradient_canvas()
    patch = _checkerboard_patch()
    canvas[10:30, 100:120] = patch
    canvas[80:100, 100:120] = patch
    canvas[150:170, 100:120] = patch

    matches = find_all_templates(canvas, patch, threshold=0.9, min_distance_px=20)

    assert [match.y for match in matches] == [10, 80, 150]


def test_find_all_templates_suppresses_near_duplicate_peaks():
    canvas = _gradient_canvas()
    patch = _checkerboard_patch()
    canvas[50:70, 100:120] = patch

    matches = find_all_templates(canvas, patch, threshold=0.9, min_distance_px=20)

    assert len(matches) == 1
