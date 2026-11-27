import numpy as np
import pytest

import imaging.algorithms as alg
from imaging.algorithms import (
    ALGORITHMS,
    PARAM_SPECS,
    VERSIONS,
    default_params,
    normalize_params,
    process,
)


def _low_contrast_image() -> np.ndarray:
    """100~120 사이 밝기만 쓰는 저대비 영상 + 가는 세로선(흉막선 흉내)."""
    rng = np.random.default_rng(0)
    img = rng.integers(100, 115, size=(128, 128), dtype=np.uint8)
    img[:, 64] = 120
    return img


def _step_image() -> np.ndarray:
    """왼쪽 절반 80, 오른쪽 절반 160인 잡음 없는 영상. 경계는 열 31|32 사이."""
    img = np.full((64, 64), 80, dtype=np.uint8)
    img[:, 32:] = 160
    return img


# ----- 4종 공통 약속 -----

@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_output_is_same_size_uint8(algorithm):
    img = _low_contrast_image()
    out = process(img, default_params(algorithm))
    assert out.dtype == np.uint8 and out.shape == img.shape


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_original_is_not_modified(algorithm):
    img = _low_contrast_image()
    before = img.copy()
    process(img, default_params(algorithm))
    assert np.array_equal(img, before)


def test_every_algorithm_is_connected_everywhere():
    # 리뷰 #9: 표 하나에만 추가하고 다른 곳을 빠뜨리는 실수를 막는다
    assert set(ALGORITHMS) == set(PARAM_SPECS) == set(alg._FUNCS) == set(VERSIONS)


# ----- CLAHE·Gaussian -----

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


# ----- Unsharp -----

def test_unsharp_boosts_edge_and_keeps_flat_area():
    img = _step_image()
    out = process(img, {"algorithm": "unsharp", "amount": 1.0, "ksize": 5})
    row = out[32].astype(int)
    # 경계 바로 옆: 어두운 쪽은 더 어둡게, 밝은 쪽은 더 밝게 (선이 또렷해짐)
    assert row[31] < 80 and row[32] > 160
    # 경계에서 먼 평평한 곳은 그대로
    assert row[5] == 80 and row[58] == 160


def test_bigger_amount_gives_stronger_edge():
    img = _step_image()
    weak = process(img, {"algorithm": "unsharp", "amount": 0.5}).astype(int)
    strong = process(img, {"algorithm": "unsharp", "amount": 2.0}).astype(int)
    assert strong[32, 32] - strong[32, 31] > weak[32, 32] - weak[32, 31]


def test_unsharp_result_stays_in_0_255():
    # 0과 255가 맞닿은 경계: 계산값은 범위를 넘지만 잘려서(saturate) 0·255로 남아야 한다
    img = np.zeros((32, 32), dtype=np.uint8)
    img[:, 16:] = 255
    out = process(img, {"algorithm": "unsharp", "amount": 5.0})
    assert out[:, :16].max() == 0 and out[:, 16:].min() == 255


# ----- Sobel -----

def test_sobel_finds_edge_only():
    out = process(_step_image(), {"algorithm": "sobel"})
    assert out[:, 31:33].min() == 255   # 경계 = 가장 센 값
    assert out[:, :29].max() == 0       # 평평한 곳 = 0
    assert out[:, 35:].max() == 0


def test_sobel_on_flat_image_is_all_zero():
    out = process(np.full((16, 16), 120, dtype=np.uint8), {"algorithm": "sobel"})
    assert out.max() == 0


# ----- normalize_params (리뷰 #9) -----

def test_normalize_fills_defaults():
    assert normalize_params({"algorithm": "clahe"}) == {
        "algorithm": "clahe", "clip_limit": 2.0, "tile_size": 8,
    }


def test_normalize_fixes_types_and_does_not_touch_input():
    params = {"algorithm": "unsharp", "amount": 2, "ksize": 7.0}
    p = normalize_params(params)
    assert p == {"algorithm": "unsharp", "amount": 2.0, "ksize": 7, "sigma": 0.0}
    assert type(p["amount"]) is float and type(p["ksize"]) is int
    assert params == {"algorithm": "unsharp", "amount": 2, "ksize": 7.0}


def test_missing_params_use_defaults():
    img = _low_contrast_image()
    assert np.array_equal(process(img, {"algorithm": "clahe"}), process(img, default_params("clahe")))


def test_normalized_params_reproduce_same_result():
    # 처리 이력에 저장한 값으로 다시 돌리면 같은 결과가 나와야 한다
    img = _low_contrast_image()
    params = {"algorithm": "unsharp", "amount": 1.5}
    assert np.array_equal(process(img, params), process(img, normalize_params(params)))


# ----- 잘못된 입력 -----

@pytest.mark.parametrize(
    "params, message",
    [
        ({"algorithm": "nope"}, "알 수 없는 알고리즘"),
        ({}, "알 수 없는 알고리즘"),
        ({"algorithm": "clahe", "clip_limit": 0}, "범위"),
        ({"algorithm": "clahe", "clip_limit": "2"}, "숫자"),
        ({"algorithm": "clahe", "tile_size": 2.5}, "정수"),
        ({"algorithm": "clahe", "tile_size": True}, "숫자"),
        ({"algorithm": "clahe", "cliplimit": 2.0}, "없는 파라미터"),
        ({"algorithm": "gaussian", "ksize": 4}, "홀수"),
        ({"algorithm": "gaussian", "ksize": 99}, "범위"),
        ({"algorithm": "unsharp", "amount": 0}, "범위"),
        ({"algorithm": "unsharp", "ksize": 6}, "홀수"),
        ({"algorithm": "sobel", "ksize": 4}, "홀수"),
        ({"algorithm": "sobel", "ksize": 9}, "범위"),
        ({"algorithm": "sobel", "sigma": 1.0}, "없는 파라미터"),
    ],
)
def test_bad_params_are_rejected(params, message):
    with pytest.raises(ValueError, match=message):
        process(_low_contrast_image(), params)


def test_params_must_be_dict():
    with pytest.raises(ValueError, match="dict"):
        normalize_params(["clahe"])


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


def test_broken_result_is_caught(monkeypatch):
    # 리뷰 #9: assert 대신 직접 검사하므로 python -O에서도 약속 위반을 잡는다
    monkeypatch.setitem(alg._FUNCS, "gaussian", lambda image, **p: image.astype(np.float32))
    with pytest.raises(RuntimeError, match="약속"):
        process(_low_contrast_image(), {"algorithm": "gaussian"})
