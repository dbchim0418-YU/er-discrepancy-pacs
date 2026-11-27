import numpy as np
import pytest

from imaging.rle import case_mask, load_rle_csv, mask_to_rle, rank_by_area, rle_to_mask


def test_docstring_example_by_hand():
    # 3x3, "1 2 3 1": 열 방향 번호 1·2번과 6번이 기흉
    #   0 3 6        0 0 1
    #   1 4 7   →    1 0 0
    #   2 5 8        1 0 0
    expected = np.array([[0, 0, 1],
                         [1, 0, 0],
                         [1, 0, 0]], dtype=np.uint8)
    assert np.array_equal(rle_to_mask("1 2 3 1", 3, 3), expected)


def test_pixel_order_is_column_first():
    # 너비 4, 높이 2. 처음 2칸 = 맨 왼쪽 열 전체(행 방향이었다면 맨 윗줄 왼쪽 2칸)
    mask = rle_to_mask("0 2", width=4, height=2)
    assert mask.shape == (2, 4)
    assert mask[:, 0].tolist() == [1, 1] and mask[:, 1:].sum() == 0


def test_no_pneumothorax_is_empty_mask():
    mask = rle_to_mask(" -1", 5, 4)
    assert mask.shape == (4, 5) and mask.dtype == np.uint8 and mask.sum() == 0
    assert mask_to_rle(mask) == "-1"


def test_round_trip_random_mask():
    rng = np.random.default_rng(0)
    mask = (rng.random((37, 23)) > 0.7).astype(np.uint8)
    rle = mask_to_rle(mask)
    assert np.array_equal(rle_to_mask(rle, width=23, height=37), mask)


def test_mask_to_rle_by_hand():
    mask = np.array([[0, 0, 1],
                     [1, 0, 0],
                     [1, 0, 0]], dtype=np.uint8)
    assert mask_to_rle(mask) == "1 2 3 1"


def test_full_mask_and_last_pixel():
    assert rle_to_mask("0 6", 3, 2).sum() == 6
    assert rle_to_mask("5 1", 3, 2)[1, 2] == 1   # 마지막 픽셀(오른쪽 아래)


def test_case_mask_merges_regions():
    m = case_mask(["0 1", "8 1"], 3, 3)   # 왼쪽 위 + 오른쪽 아래
    assert m.sum() == 2 and m[0, 0] == 1 and m[2, 2] == 1


@pytest.mark.parametrize(
    "rle, message",
    [
        ("1 2 3", "짝수"),
        ("1 -2", "음수"),
        ("1 0", "1 이상"),
        ("a 2", "숫자가 아닌"),
        ("", "비어"),
        ("5 10", "영상 밖"),       # 3x3=9칸인데 15번까지 필요
        (None, "문자열"),
    ],
)
def test_bad_rle_is_rejected(rle, message):
    with pytest.raises(ValueError, match=message):
        rle_to_mask(rle, 3, 3)


@pytest.mark.parametrize("width, height", [(0, 3), (3, -1), (2.5, 3), (True, 3)])
def test_bad_size_is_rejected(width, height):
    with pytest.raises(ValueError, match="정수"):
        rle_to_mask("-1", width, height)


def test_load_csv_and_rank_by_area(tmp_path):
    # 원본처럼 머리글 쉼표 뒤에 공백, 값 앞에 공백, 한 영상이 두 줄
    csv_file = tmp_path / "train-rle.csv"
    csv_file.write_text(
        "ImageId, EncodedPixels\n"
        "big, 0 5\n"
        "none, -1\n"
        "two, 0 1\n"
        "two, 7 1\n"
        "small, 4 1\n",
        encoding="utf-8",
    )
    cases = load_rle_csv(csv_file)
    assert cases["two"] == ["0 1", "7 1"] and cases["none"] == ["-1"]

    ranked = rank_by_area(cases, width=3, height=3)
    assert [c["image_id"] for c in ranked] == ["small", "two", "big"]   # 기흉 없는 영상은 빠짐
    assert ranked[1] == {"image_id": "two", "area": 2, "area_ratio": 22.222, "regions": 2}


def test_load_csv_rejects_other_files(tmp_path):
    other = tmp_path / "other.csv"
    other.write_text("id,label\n1,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="형식"):
        load_rle_csv(other)
