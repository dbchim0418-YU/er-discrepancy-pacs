"""영상처리 알고리즘. 주인: 주연

약속(개발 규칙 2번):
- 입력: 흑백 uint8 배열(0~255), params dict
- 출력: 입력과 같은 크기의 uint8 배열
- 원본 배열은 수정하지 않는다(복사본에서 처리)

처리 이력에는 normalize_params()가 돌려준 실제 적용 값과 VERSIONS[algorithm]을 함께 저장한다.
"""
from __future__ import annotations

import cv2
import numpy as np

ALGORITHMS = ["clahe", "gaussian", "unsharp", "sobel"]

# 처리 이력(processing.version)에 함께 저장한다. 처리 방식이 바뀌면 숫자를 올린다.
VERSIONS = {"clahe": "1", "gaussian": "1", "unsharp": "1", "sobel": "1"}

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
    "unsharp": {
        "amount": (float, 0.1, 5.0, 1.0),       # 경계를 얼마나 더할지. 클수록 선명해지고 잡음도 커진다
        "ksize": (int, 3, 31, 5),               # 흐린 영상을 만들 Gaussian 커널 크기(홀수)
        "sigma": (float, 0.0, 10.0, 0.0),       # 0이면 ksize에서 자동 계산
    },
    "sobel": {
        "ksize": (int, 3, 7, 3),                # 미분 커널 크기(3, 5, 7). 클수록 굵은 경계를 잡고 잡음에 덜 민감하다
    },
}

# 커널 크기는 가운데 픽셀이 있어야 해서 홀수만 쓴다.
ODD_PARAMS = {"ksize"}


def default_params(algorithm: str) -> dict:
    """화면 초기값용. 예: {"algorithm": "clahe", "clip_limit": 2.0, "tile_size": 8}"""
    if algorithm not in PARAM_SPECS:
        raise ValueError(f"알 수 없는 알고리즘입니다: {algorithm}")
    params = {name: spec[3] for name, spec in PARAM_SPECS[algorithm].items()}
    return {"algorithm": algorithm, **params}


def normalize_params(params: dict) -> dict:
    """검사를 통과한 '실제로 적용되는' 파라미터를 돌려준다.

    빠진 값은 기본값으로 채우고 타입을 맞춘다.
    예: {"algorithm": "clahe"} → {"algorithm": "clahe", "clip_limit": 2.0, "tile_size": 8}
    처리 이력에는 이 값을 저장해야 나중에 기본값이 바뀌어도 같은 결과를 재현할 수 있다.
    """
    if not isinstance(params, dict):
        raise ValueError("params는 dict여야 합니다.")
    algorithm = params.get("algorithm")
    if algorithm not in PARAM_SPECS:
        raise ValueError(f"알 수 없는 알고리즘입니다: {algorithm}. 사용 가능: {', '.join(ALGORITHMS)}")
    return {"algorithm": algorithm, **_validate_params(algorithm, params)}


def process(image: np.ndarray, params: dict) -> np.ndarray:
    """params["algorithm"]에 따라 알고리즘을 적용한다.

    예: process(img, {"algorithm": "clahe", "clip_limit": 2.0, "tile_size": 8})
    빠진 파라미터는 기본값을 쓰고, 잘못된 파라미터는 ValueError로 이유와 함께 거절한다.
    """
    _check_image(image)
    p = normalize_params(params)
    algorithm = p.pop("algorithm")

    src = image.copy()  # OpenCV가 원본을 건드리지 않도록 복사본으로 처리
    result = _FUNCS[algorithm](src, **p)

    # 약속 확인: 같은 크기의 uint8.
    # assert는 python -O로 실행하면 사라지므로 직접 검사한다.
    # 사용자 입력 문제가 아니라 이 파일의 버그라서 RuntimeError로 구분한다.
    if result.dtype != np.uint8 or result.shape != image.shape:
        raise RuntimeError(
            f"{algorithm} 결과가 약속과 다릅니다: {result.dtype} {result.shape} (기대: uint8 {image.shape})"
        )
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


def _unsharp(image: np.ndarray, amount: float, ksize: int, sigma: float) -> np.ndarray:
    """Unsharp Masking: 원본 - 흐린 영상 = 경계(세부)만 남은 영상.
    이 경계를 amount배 해서 원본에 더하면 선이 선명해진다.
        결과 = 원본 + amount * (원본 - 흐린 영상)
             = (1 + amount) * 원본 - amount * 흐린 영상
    내부에서 Gaussian을 쓰지만 목적은 반대다(Gaussian은 평활화, Unsharp는 선명화).
    평평한 영역은 원본 - 흐린 영상이 0에 가까워 거의 바뀌지 않고, 잡음은 함께 커진다."""
    blurred = _gaussian(image, ksize, sigma)
    # addWeighted는 0 미만·255 초과를 잘라(saturate) uint8로 돌려준다.
    return cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)


def _sobel(image: np.ndarray, ksize: int) -> np.ndarray:
    """Sobel: 가로(x)·세로(y) 방향 밝기 변화량을 구해 경계 세기 sqrt(gx² + gy²)를 만든다.
    밝기가 그대로인 곳은 0(검정), 급하게 바뀌는 곳(흉막선·갈비뼈 테두리)은 밝게 보인다.
    값의 범위가 영상마다 달라 가장 센 경계를 255로 맞춰 보여준다(영상끼리 절대값 비교는 불가)."""
    # uint8로 미분하면 음수(밝→어두운 경계)가 잘리므로 float64로 계산한다.
    gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=ksize)
    magnitude = np.hypot(gx, gy)

    peak = magnitude.max()
    if peak == 0:  # 완전히 평평한 영상: 경계가 없으므로 전부 0 (0으로 나누기 방지)
        return np.zeros_like(image)
    return np.round(magnitude / peak * 255).astype(np.uint8)


# 알고리즘 이름 → 함수. 함수 인자 이름은 PARAM_SPECS의 파라미터 이름과 같아야 한다.
# (리뷰 #9: if/elif로 두면 새 알고리즘을 추가할 때 빠뜨리기 쉬워서 표로 묶었다)
_FUNCS = {
    "clahe": _clahe,
    "gaussian": _gaussian,
    "unsharp": _unsharp,
    "sobel": _sobel,
}


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
        if name in ODD_PARAMS and value % 2 == 0:
            raise ValueError(f"{name}는 홀수여야 합니다: {value}")
        clean[name] = value
    return clean
