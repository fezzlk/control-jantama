from __future__ import annotations

import numpy as np


def images_are_similar(a: np.ndarray, b: np.ndarray, threshold: float = 0.98) -> bool:
    """2枚の画像がほぼ同じ内容かどうかを平均絶対差分から判定する。

    雀魂側の遅延ロード完了判定（スクリーンショットが変化しなくなった＝安定）と、
    スクロールしても新しい行が現れなかった＝一覧末尾に到達した、の両方に使う。
    形状が異なる場合は比較不能として非類似とみなす。
    """
    if a.shape != b.shape:
        return False

    mean_abs_diff = float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())
    similarity = 1.0 - (mean_abs_diff / 255.0)
    return similarity >= threshold
