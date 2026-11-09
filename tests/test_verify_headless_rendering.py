import numpy as np
import pytest

from scripts.verify_headless_rendering import image_stats, main, similarity


def _image(fill: int) -> np.ndarray:
    return np.full((40, 60, 3), fill, dtype=np.uint8)


def test_black_image_is_not_rendered():
    stats = image_stats(_image(0))
    assert stats.dark_ratio == 1.0
    assert not stats.looks_rendered


def test_flat_gray_image_is_not_rendered():
    stats = image_stats(_image(128))
    assert stats.stddev == 0.0
    assert stats.distinct_colors == 1
    assert not stats.looks_rendered


def test_varied_image_is_rendered():
    rng = np.random.default_rng(0)
    image = rng.integers(0, 256, size=(40, 60, 3), dtype=np.uint8)
    stats = image_stats(image)
    assert stats.looks_rendered
    assert stats.distinct_colors > 100


def test_similarity_identical_and_shape_mismatch():
    assert similarity(_image(10), _image(10)) == 1.0
    assert similarity(_image(0), _image(255)) == 0.0
    assert similarity(_image(0), np.zeros((10, 10, 3), dtype=np.uint8)) is None


def test_refuses_live_user_data_dir(tmp_path):
    with pytest.raises(SystemExit):
        main(["--output-dir", str(tmp_path), "--user-data-dir", "data/user_data_dir"])
