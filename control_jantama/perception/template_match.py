from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class Match:
    x: int
    y: int
    width: int
    height: int
    score: float

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


def find_template(image: np.ndarray, template: np.ndarray, threshold: float = 0.85) -> Match | None:
    """imageの中からtemplateに最もよく一致する位置を探す。

    閾値未満なら None を返す（未知状態を推測で埋めない、という設計原則）。
    """
    if image.shape[0] < template.shape[0] or image.shape[1] < template.shape[1]:
        return None

    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    x, y = max_loc
    height, width = template.shape[:2]
    return Match(x=x, y=y, width=width, height=height, score=float(max_val))


def find_all_templates(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.85,
    min_distance_px: int = 20,
    max_matches: int = 200,
) -> list[Match]:
    """imageの中からtemplateに一致する箇所を全て探す（non-max suppression）。

    仮想リストで同じアイコンが画面内に複数表示される場面を想定しており、
    採用した一致箇所の周囲min_distance_px四方を潰してから次点を探す、という
    処理をthreshold未満になるかmax_matchesに達するまで繰り返す。
    戻り値はy昇順（画面上から下＝一覧の並び順）。
    """
    if image.shape[0] < template.shape[0] or image.shape[1] < template.shape[1]:
        return []

    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    height, width = template.shape[:2]

    matches: list[Match] = []
    for _ in range(max_matches):
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            break

        x, y = max_loc
        matches.append(Match(x=x, y=y, width=width, height=height, score=float(max_val)))

        y0 = max(0, y - min_distance_px)
        y1 = min(result.shape[0], y + min_distance_px)
        x0 = max(0, x - min_distance_px)
        x1 = min(result.shape[1], x + min_distance_px)
        result[y0:y1, x0:x1] = -1.0

    return sorted(matches, key=lambda match: match.y)


def decode_image(image_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("画像のデコードに失敗しました")
    return image


def load_template(path: str | Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"テンプレート画像が見つかりません: {path}")
    return image
