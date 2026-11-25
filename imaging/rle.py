"""SIIM-ACR RLE 마스크 풀기. 주인: 주연"""
from __future__ import annotations

import numpy as np


def rle_to_mask(rle: str, width: int, height: int) -> np.ndarray:
    """train-rle.csv의 EncodedPixels를 0/1 마스크로 바꾼다. "-1"이면 기흉 없음(빈 마스크).

    TODO(주연): 구현, 마스크 면적으로 작은 기흉 사례 고르기
    """
    raise NotImplementedError
