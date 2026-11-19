"""영상처리 알고리즘. 주인: 주연

약속(개발 규칙 2번):
- 입력: 흑백 uint8 배열(0~255), params dict
- 출력: 입력과 같은 크기의 uint8 배열
- 원본 배열은 수정하지 않는다(복사본에서 처리)
"""
from __future__ import annotations

import numpy as np

ALGORITHMS = ["clahe", "gaussian", "unsharp", "sobel"]


def process(image: np.ndarray, params: dict) -> np.ndarray:
    """params["algorithm"]에 따라 알고리즘을 적용한다.

    예: process(img, {"algorithm": "clahe", "clip_limit": 2.0, "tile_size": 8})
    TODO(주연): 알고리즘 4종 구현, 잘못된 파라미터는 ValueError로 이유와 함께 거절
    """
    raise NotImplementedError
