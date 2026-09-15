import numpy as np

from control_jantama.perception.screen_diff import images_are_similar


def _solid_image(value: int, height: int = 50, width: int = 50) -> np.ndarray:
    return np.full((height, width, 3), value, dtype=np.uint8)


def test_images_are_similar_for_identical_images():
    a = _solid_image(100)
    b = _solid_image(100)

    assert images_are_similar(a, b, threshold=0.98) is True


def test_images_are_similar_false_for_large_difference():
    a = _solid_image(0)
    b = _solid_image(255)

    assert images_are_similar(a, b, threshold=0.98) is False


def test_images_are_similar_false_for_mismatched_shapes():
    a = _solid_image(100, height=50, width=50)
    b = _solid_image(100, height=60, width=50)

    assert images_are_similar(a, b, threshold=0.98) is False
