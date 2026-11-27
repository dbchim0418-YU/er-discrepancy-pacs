import numpy as np
import pytest

from imaging.roi import compare_roi, roi_stats, validate_roi


def _image() -> np.ndarray:
    """6x8 영상. 값 = 행*10 + 열 이라서 손으로 계산하기 쉽다."""
    rows, cols = np.mgrid[0:6, 0:8]
    return (rows * 10 + cols).astype(np.uint8)


def test_stats_match_hand_calculation():
    # x=1, y=2, w=3, h=2 → 행 2~3, 열 1~3 → [21,22,23, 31,32,33]
    s = roi_stats(_image(), {"x": 1, "y": 2, "w": 3, "h": 2})
    assert s["pixel_count"] == 6
    assert s["mean"] == pytest.approx(27.0)
    assert s["var"] == pytest.approx(np.var([21, 22, 23, 31, 32, 33]))
    assert s["std"] == pytest.approx(np.sqrt(s["var"]))
    assert (s["min"], s["max"], s["median"]) == (21, 33, 27.0)


def test_histogram_counts_each_value():
    s = roi_stats(_image(), {"x": 1, "y": 2, "w": 3, "h": 2})
    hist = s["histogram"]
    assert len(hist) == 256 and sum(hist) == 6
    assert hist[21] == 1 and hist[33] == 1 and hist[0] == 0


def test_whole_image_roi_is_allowed():
    img = _image()
    s = roi_stats(img, {"x": 0, "y": 0, "w": 8, "h": 6})
    assert s["pixel_count"] == img.size
    assert s["mean"] == pytest.approx(img.mean())


def test_result_is_plain_python_types_for_firestore():
    s = roi_stats(_image(), {"x": 0, "y": 0, "w": 2, "h": 2})
    for key in ("pixel_count", "min", "max"):
        assert type(s[key]) is int
    for key in ("mean", "std", "var", "median"):
        assert type(s[key]) is float
    assert type(s["histogram"]) is list and type(s["histogram"][0]) is int
    assert all(type(v) is int for v in s["roi"].values())


def test_integer_valued_float_and_numpy_int_are_accepted():
    r = validate_roi({"x": 1.0, "y": np.int64(2), "w": 3, "h": 2}, (6, 8))
    assert r == {"x": 1, "y": 2, "w": 3, "h": 2}


def test_compare_roi_shows_contrast_change():
    img = _image()
    stretched = (img.astype(np.int32) * 2).clip(0, 255).astype(np.uint8)
    c = compare_roi(img, stretched, {"x": 0, "y": 0, "w": 8, "h": 6})
    assert c["diff"]["mean"] == pytest.approx(c["after"]["mean"] - c["before"]["mean"])
    assert c["diff"]["std"] > 0


def test_compare_roi_has_roi_and_image_shape_on_top():
    # 리뷰 #11: 리포트에서 바로 꺼내 쓰도록 최상위에 좌표와 영상 크기를 둔다
    img = _image()
    c = compare_roi(img, img.copy(), {"x": 1, "y": 2, "w": 3, "h": 2})
    assert c["roi"] == {"x": 1, "y": 2, "w": 3, "h": 2} == c["before"]["roi"]
    assert c["image_shape"] == [6, 8]
    assert all(type(n) is int for n in c["image_shape"])


def test_compare_roi_rejects_different_sizes():
    with pytest.raises(ValueError, match="크기가 다릅니다"):
        compare_roi(_image(), np.zeros((3, 3), dtype=np.uint8), {"x": 0, "y": 0, "w": 1, "h": 1})


@pytest.mark.parametrize(
    "roi, message",
    [
        ({"x": 0, "y": 0, "w": 0, "h": 2}, "1 이상"),
        ({"x": 0, "y": 0, "w": 2, "h": -1}, "1 이상"),
        ({"x": -1, "y": 0, "w": 2, "h": 2}, "영상 밖"),
        ({"x": 7, "y": 0, "w": 2, "h": 2}, "영상 밖"),   # 오른쪽으로 1칸 넘침
        ({"x": 0, "y": 5, "w": 2, "h": 2}, "영상 밖"),   # 아래로 1칸 넘침
        ({"x": 0, "y": 0, "w": 2}, "빠진 값"),
        ({"x": 0.5, "y": 0, "w": 2, "h": 2}, "정수"),
        ({"x": "1", "y": 0, "w": 2, "h": 2}, "정수"),
        ({"x": True, "y": 0, "w": 2, "h": 2}, "정수"),
        ({"x": float("nan"), "y": 0, "w": 2, "h": 2}, "정수"),
        ([0, 0, 2, 2], "형태"),
    ],
)
def test_bad_roi_is_rejected(roi, message):
    with pytest.raises(ValueError, match=message):
        roi_stats(_image(), roi)


def test_bad_image_is_rejected():
    with pytest.raises(ValueError, match="uint8"):
        roi_stats(np.zeros((4, 4), dtype=np.float32), {"x": 0, "y": 0, "w": 1, "h": 1})
