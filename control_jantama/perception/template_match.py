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
