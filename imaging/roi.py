"""ROI 선택과 통계. 주인: 주연"""
from __future__ import annotations

import numpy as np


def roi_stats(image: np.ndarray, roi: dict) -> dict:
    """roi = {"x": int, "y": int, "w": int, "h": int} 영역의 평균·분산·히스토그램.

    TODO(주연): 구현, 영상 밖이거나 크기가 0인 ROI는 ValueError로 거절
    """
    raise NotImplementedError
