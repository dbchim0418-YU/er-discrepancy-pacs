import numpy as np
import pytest

from imaging.algorithms import default_params, process


def _low_contrast_image() -> np.ndarray:
    """100~120 사이 밝기만 쓰는 저대비 영상 + 가는 세로선(흉막선 흉내)."""
    rng = np.random.default_rng(0)
    img = rng.integers(100, 115, size=(128, 128), dtype=np.uint8)
    img[:, 64] = 120
    return img


@pytest.mark.parametrize("algorithm", ["clahe", "gaussian"])
def test_output_is_same_size_uint8(algorithm):
    img = _low_contrast_image()
    out = process(img, default_params(algorithm))
    assert out.dtype == np.uint8 and out.shape == img.shape


@pytest.mark.parametrize("algorithm", ["clahe", "gaussian"])
def test_original_is_not_modified(algorithm):
    img = _low_contrast_image()
    before = img.copy()
    process(img, default_params(algorithm))
    assert np.array_equal(img, before)


def test_clahe_increases_contrast():
    img = _low_contrast_image()
    out = process(img, {"algorithm": "clahe", "clip_limit": 4.0, "tile_size": 8})
    assert out.std() > img.std()


def test_higher_clip_limit_gives_more_contrast():
    img = _low_contrast_image()
    weak = process(img, {"algorithm": "clahe", "clip_limit": 1.0})
    strong = process(img, {"algorithm": "clahe", "clip_limit": 8.0})
    assert strong.std() > weak.std()


def test_gaussian_reduces_noise():
    img = _low_contrast_image()
    out = process(img, {"algorithm": "gaussian", "ksize": 7})
    assert out.std() < img.std()


def test_missing_params_use_defaults():
    img = _low_contrast_image()
    assert np.array_equal(process(img, {"algorithm": "clahe"}), process(img, default_params("clahe")))


@pytest.mark.parametrize(
    "params, message",
    [
        ({"algorithm": "nope"}, "알 수 없는 알고리즘"),
        ({"algorithm": "clahe", "clip_limit": 0}, "범위"),
        ({"algorithm": "clahe", "clip_limit": "2"}, "숫자"),
        ({"algorithm": "clahe", "tile_size": 2.5}, "정수"),
        ({"algorithm": "clahe", "tile_size": True}, "숫자"),
        ({"algorithm": "clahe", "cliplimit": 2.0}, "없는 파라미터"),
        ({"algorithm": "gaussian", "ksize": 4}, "홀수"),
        ({"algorithm": "gaussian", "ksize": 99}, "범위"),
    ],
)
def test_bad_params_are_rejected(params, message):
    with pytest.raises(ValueError, match=message):
        process(_low_contrast_image(), params)


@pytest.mark.parametrize(
    "image",
    [
        np.zeros((8, 8), dtype=np.float32),    # uint8 아님
        np.zeros((8, 8, 3), dtype=np.uint8),   # 컬러
        np.zeros((0, 0), dtype=np.uint8),      # 빈 영상
    ],
)
def test_bad_image_is_rejected(image):
    with pytest.raises(ValueError):
        process(image, {"algorithm": "clahe"})
