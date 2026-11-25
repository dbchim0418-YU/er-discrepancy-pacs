import numpy as np
import pytest

from core.viewer import validate_images


def test_valid_pair_passes():
    img = np.zeros((4, 5), dtype=np.uint8)
    validate_images(img, img.copy())


def test_float_result_is_rejected():
    img = np.zeros((4, 5), dtype=np.uint8)
    with pytest.raises(ValueError, match="처리 결과 영상"):
        validate_images(img, img.astype(np.float32))


def test_different_size_result_is_rejected():
    img = np.zeros((4, 5), dtype=np.uint8)
    with pytest.raises(ValueError, match="크기"):
        validate_images(img, np.zeros((5, 5), dtype=np.uint8))


def test_color_original_is_rejected():
    with pytest.raises(ValueError, match="원본 영상"):
        validate_images(np.zeros((4, 5, 3), dtype=np.uint8))
