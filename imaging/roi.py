"""ROI 선택과 통계. 주인: 주연

ROI 좌표는 2_Imaging.py에서 숫자로 입력받는다(PR #2 리뷰에서 정함).
- roi = {"x": 왼쪽 위 열, "y": 왼쪽 위 행, "w": 너비, "h": 높이} (단위: 픽셀)
- 영상 배열에서는 image[y:y+h, x:x+w] 영역이다.
- 통계는 load_image()가 돌려준 0~255 값(윈도우 적용 후)으로 계산한다.
  DICOM 원래 값(HU 등)이 아니므로 보고서에 "표시 밝기 기준"이라고 적는다.

결과는 Firestore에 바로 저장할 수 있게 파이썬 기본 타입(int, float, list)으로 돌려준다.
"""
from __future__ import annotations

import numpy as np

ROI_KEYS = ("x", "y", "w", "h")


def roi_stats(image: np.ndarray, roi: dict) -> dict:
    """roi 영역의 밝기 통계와 히스토그램.

    돌려주는 값:
      roi            검사를 통과한 좌표 {"x", "y", "w", "h"}
      pixel_count    픽셀 수 (w * h)
      mean, std, var 평균, 표준편차, 분산
      min, max, median
      histogram      0~255 밝기별 픽셀 수 (길이 256)
    """
    _check_image(image)
    r = validate_roi(roi, image.shape)
    region = image[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]]

    values = region.astype(np.float64)
    return {
        "roi": r,
        "pixel_count": int(region.size),
        "mean": float(values.mean()),
        "std": float(values.std()),
        "var": float(values.var()),
        "min": int(region.min()),
        "max": int(region.max()),
        "median": float(np.median(values)),
        "histogram": np.bincount(region.ravel(), minlength=256).tolist(),
    }


def compare_roi(original: np.ndarray, processed: np.ndarray, roi: dict) -> dict:
    """같은 ROI에서 원본과 처리 결과의 통계를 비교한다.

    돌려주는 값:
      roi          검사를 통과한 좌표 (before·after의 roi와 같다. 리포트에서 바로 꺼내 쓰기용)
      image_shape  [높이, 너비]. 좌표가 영상의 어느 부분인지 알려면 영상 크기가 함께 필요하다
      before       원본 통계,  after  결과 통계,  diff  결과 - 원본
    diff의 std가 커지면 대비가 강해진 것(CLAHE), 작아지면 잡음이 줄거나 흐려진 것(Gaussian)이다.
    변화율(%)은 workflow/report.py에서 계산한다(리뷰 #11에서 정함).
    """
    _check_image(original)
    _check_image(processed)
    if original.shape != processed.shape:
        raise ValueError(f"원본 {original.shape}과 처리 결과 {processed.shape}의 크기가 다릅니다.")

    before = roi_stats(original, roi)
    after = roi_stats(processed, roi)
    diff = {k: after[k] - before[k] for k in ("mean", "std", "var", "min", "max", "median")}
    return {
        "roi": before["roi"],
        "image_shape": [int(n) for n in original.shape],
        "before": before,
        "after": after,
        "diff": diff,
    }


def validate_roi(roi: dict, shape: tuple[int, int]) -> dict:
    """ROI 좌표를 검사하고 {"x", "y", "w", "h"} 정수 dict로 돌려준다.

    영상 밖으로 나가거나 크기가 0인 ROI는 자르지 않고 거절한다.
    (몰래 잘라서 계산하면 기록된 좌표와 실제 계산 영역이 달라져 재현이 안 되기 때문)
    """
    if not isinstance(roi, dict):
        raise ValueError("ROI는 {'x', 'y', 'w', 'h'} 형태여야 합니다.")
    missing = [k for k in ROI_KEYS if k not in roi]
    if missing:
        raise ValueError(f"ROI에 빠진 값이 있습니다: {', '.join(missing)}")

    r = {}
    for k in ROI_KEYS:
        v = roi[k]
        # bool은 int의 하위 타입이라 따로 막는다. 3.0처럼 정수인 실수는 허용한다.
        # nan·inf는 int()에서 다른 오류가 나므로 먼저 거른다.
        if (
            isinstance(v, bool)
            or not isinstance(v, (int, float, np.integer))
            or not np.isfinite(v)
            or int(v) != v
        ):
            raise ValueError(f"ROI {k}는 정수여야 합니다: {v!r}")
        r[k] = int(v)

    height, width = shape
    if r["w"] <= 0 or r["h"] <= 0:
        raise ValueError(f"ROI 너비·높이는 1 이상이어야 합니다: w={r['w']}, h={r['h']}")
    if r["x"] < 0 or r["y"] < 0 or r["x"] + r["w"] > width or r["y"] + r["h"] > height:
        raise ValueError(
            f"ROI가 영상 밖으로 나갑니다: x={r['x']}~{r['x'] + r['w']}, y={r['y']}~{r['y'] + r['h']} "
            f"(영상 크기: 너비 {width}, 높이 {height})"
        )
    return r


def _check_image(image) -> None:
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 2:
        raise ValueError("영상은 흑백 uint8 2차원 배열이어야 합니다.")
