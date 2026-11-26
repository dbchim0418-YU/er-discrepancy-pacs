"""영상처리 알고리즘. 주인: 주연

약속(개발 규칙 2번):
- 입력: 흑백 uint8 배열(0~255), params dict
- 출력: 입력과 같은 크기의 uint8 배열
- 원본 배열은 수정하지 않는다(복사본에서 처리)
"""
from __future__ import annotations

import cv2
import numpy as np

ALGORITHMS = ["clahe", "gaussian", "unsharp", "sobel"]

# 처리 이력(processing.version)에 함께 저장한다. 처리 방식이 바뀌면 숫자를 올린다.
VERSIONS = {"clahe": "1", "gaussian": "1"}

# 파라미터 규칙: 이름 → (타입, 최솟값, 최댓값, 기본값)
# 화면의 슬라이더 범위와 입력 검사에 같은 표를 쓴다.
PARAM_SPECS = {
    "clahe": {
        "clip_limit": (float, 0.1, 40.0, 2.0),  # 히스토그램을 자르는 높이. 클수록 대비가 강해지고 잡음도 커진다
        "tile_size": (int, 2, 32, 8),           # 영상을 tile_size x tile_size 칸으로 나눈다
    },
    "gaussian": {
        "ksize": (int, 3, 31, 5),               # 커널 크기(홀수). 클수록 더 흐려진다
        "sigma": (float, 0.0, 10.0, 0.0),       # 0이면 ksize에서 자동 계산
    },
}


def default_params(algorithm: str) -> dict:
    """화면 초기값용. 예: {"algorithm": "clahe", "clip_limit": 2.0, "tile_size": 8}"""
    if algorithm not in PARAM_SPECS:
        raise ValueError(f"알 수 없는 알고리즘입니다: {algorithm}")
    params = {name: spec[3] for name, spec in PARAM_SPECS[algorithm].items()}
    return {"algorithm": algorithm, **params}


def process(image: np.ndarray, params: dict) -> np.ndarray:
    """params["algorithm"]에 따라 알고리즘을 적용한다.

    예: process(img, {"algorithm": "clahe", "clip_limit": 2.0, "tile_size": 8})
    빠진 파라미터는 기본값을 쓰고, 잘못된 파라미터는 ValueError로 이유와 함께 거절한다.
    """
    _check_image(image)
    algorithm = params.get("algorithm")
    if algorithm not in ALGORITHMS:
        raise ValueError(f"알 수 없는 알고리즘입니다: {algorithm}. 사용 가능: {', '.join(ALGORITHMS)}")
    if algorithm not in PARAM_SPECS:
        raise NotImplementedError(f"{algorithm}은 아직 구현되지 않았습니다.")

    p = _validate_params(algorithm, params)
    src = image.copy()  # OpenCV가 원본을 건드리지 않도록 복사본으로 처리

    if algorithm == "clahe":
        result = _clahe(src, p["clip_limit"], p["tile_size"])
    elif algorithm == "gaussian":
        result = _gaussian(src, p["ksize"], p["sigma"])

    # 약속 확인: 같은 크기의 uint8
    assert result.dtype == np.uint8 and result.shape == image.shape
    return result


# ----- 알고리즘 -----

def _clahe(image: np.ndarray, clip_limit: float, tile_size: int) -> np.ndarray:
    """CLAHE: 영상을 칸으로 나눠 칸마다 히스토그램 평활화를 하되,
    한 밝기에 너무 많이 몰린 부분은 clip_limit에서 잘라 잡음이 과하게 커지는 것을 막는다.
    칸 경계는 이웃 칸과 보간해 계단 무늬가 생기지 않게 한다."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    return clahe.apply(image)


def _gaussian(image: np.ndarray, ksize: int, sigma: float) -> np.ndarray:
    """Gaussian 블러: 가까운 픽셀일수록 큰 가중치로 평균을 내 잡음을 줄인다.
    경계(흉막선 같은 가는 선)도 함께 흐려지는 것이 한계 → 비교 실험 대상."""
    return cv2.GaussianBlur(image, (ksize, ksize), sigmaX=sigma, sigmaY=sigma)


# ----- 검사 -----

def _check_image(image) -> None:
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 2:
        raise ValueError("입력 영상은 흑백 uint8 2차원 배열이어야 합니다.")
    if image.size == 0:
        raise ValueError("빈 영상입니다.")


def _validate_params(algorithm: str, params: dict) -> dict:
    specs = PARAM_SPECS[algorithm]

    unknown = set(params) - set(specs) - {"algorithm"}
    if unknown:
        raise ValueError(f"{algorithm}에 없는 파라미터입니다: {', '.join(sorted(unknown))}")

    clean = {}
    for name, (typ, low, high, default) in specs.items():
        value = params.get(name, default)
        # bool은 int의 하위 타입이라 따로 막는다(True가 1로 들어가는 것 방지)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}은 숫자여야 합니다: {value!r}")
        if typ is int and float(value) != int(value):
            raise ValueError(f"{name}은 정수여야 합니다: {value}")
        value = typ(value)
        if not low <= value <= high:
            raise ValueError(f"{name}은 {low}~{high} 범위여야 합니다: {value}")
        clean[name] = value

    if algorithm == "gaussian" and clean["ksize"] % 2 == 0:
        raise ValueError(f"ksize는 홀수여야 합니다: {clean['ksize']}")
    return clean
