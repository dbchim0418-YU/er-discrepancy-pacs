"""SIIM-ACR RLE 마스크 풀기. 주인: 주연

train-rle.csv 한 줄 = (ImageId, EncodedPixels).
- EncodedPixels가 "-1"이면 기흉 없음.
- 기흉 영역이 여러 개면 같은 ImageId가 여러 줄 나온다 → 합쳐서 한 마스크로 만든다.

RLE(Run-Length Encoding) = "어디서부터 몇 칸이 기흉인지"를 숫자 쌍으로 적은 압축 형식.
SIIM-ACR 형식은 일반 RLE와 두 가지가 다르다(대회 제공 mask_functions.py 기준).
  1) 픽셀 순서가 열 방향: 맨 왼쪽 열을 위→아래로 다 센 다음 다음 열로 넘어간다.
  2) 시작 위치가 상대값: 첫 숫자는 0번 픽셀부터, 그다음부터는 "앞 구간이 끝난 곳"부터 센 거리다.
예) 3x3 영상, "1 2 3 1"
    → 1칸 건너뛰고 2칸 기흉(1~2번), 다시 3칸 건너뛰고 1칸 기흉(6번)
    열 방향 번호:   0 3 6        마스크:  0 0 1
                    1 4 7                 1 0 0
                    2 5 8                 1 0 0
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

NO_PNEUMOTHORAX = "-1"


def rle_to_mask(rle: str, width: int, height: int) -> np.ndarray:
    """EncodedPixels 하나를 (height, width) uint8 0/1 마스크로 바꾼다. "-1"이면 빈 마스크."""
    _check_size(width, height)
    flat = np.zeros(width * height, dtype=np.uint8)

    numbers = _parse(rle)
    position = 0
    for gap, length in zip(numbers[0::2], numbers[1::2]):
        position += gap
        if position + length > flat.size:
            raise ValueError(
                f"RLE가 영상 밖으로 나갑니다: {position + length}번 픽셀까지 필요하지만 "
                f"영상은 {width}x{height} = {flat.size}픽셀입니다. 영상 크기를 확인하세요."
            )
        flat[position:position + length] = 1
        position += length

    # 열 방향(Fortran 순서)으로 채워 넣는다
    return flat.reshape((height, width), order="F")


def mask_to_rle(mask: np.ndarray) -> str:
    """rle_to_mask의 반대. 기흉이 없으면 "-1"."""
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        raise ValueError("마스크는 2차원 배열이어야 합니다.")
    flat = (mask.ravel(order="F") > 0).astype(np.int8)

    # 0→1로 바뀌는 곳 = 구간 시작, 1→0으로 바뀌는 곳 = 구간 끝
    padded = np.concatenate([[0], flat, [0]])
    changes = np.flatnonzero(np.diff(padded))
    starts, ends = changes[0::2], changes[1::2]
    if len(starts) == 0:
        return NO_PNEUMOTHORAX

    numbers = []
    previous_end = 0
    for start, end in zip(starts, ends):
        numbers += [int(start - previous_end), int(end - start)]
        previous_end = end
    return " ".join(map(str, numbers))


def case_mask(rles: list[str], width: int, height: int) -> np.ndarray:
    """한 영상의 RLE 여러 줄을 합친 마스크 (기흉 영역 여러 개 → 하나)."""
    mask = np.zeros((height, width), dtype=np.uint8)
    for rle in rles:
        mask |= rle_to_mask(rle, width, height)
    return mask


def load_rle_csv(path: str | Path) -> dict[str, list[str]]:
    """train-rle.csv를 읽어 {ImageId: [EncodedPixels, ...]}로 묶는다.

    원본 CSV 머리글은 "ImageId, EncodedPixels"처럼 쉼표 뒤에 공백이 있어서 열 이름의 공백을 지운다.
    """
    cases: dict[str, list[str]] = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]
        if header[:2] != ["ImageId", "EncodedPixels"]:
            raise ValueError(f"train-rle.csv 형식이 아닙니다. 머리글: {header}")
        for row in reader:
            if not row:
                continue
            image_id, rle = row[0].strip(), row[1].strip()
            cases[image_id].append(rle)
    return dict(cases)


def rank_by_area(cases: dict[str, list[str]], width: int = 1024, height: int = 1024) -> list[dict]:
    """기흉이 있는 영상만 마스크 면적이 작은 순서로 정렬한다.

    돌려주는 값: [{"image_id", "area"(픽셀 수), "area_ratio"(영상 대비 %), "regions"(RLE 줄 수)}, ...]
    면적이 작을수록 놓치기 쉬운 미세 기흉 후보다. 몇 %까지를 "작다"고 볼지는 분포를 보고 정한다.
    SIIM-ACR 영상은 모두 1024x1024라서 기본값으로 둔다.
    """
    ranked = []
    for image_id, rles in cases.items():
        positives = [r for r in rles if r.strip() != NO_PNEUMOTHORAX]
        if not positives:
            continue
        area = int(case_mask(positives, width, height).sum())
        ranked.append({
            "image_id": image_id,
            "area": area,
            "area_ratio": round(area / (width * height) * 100, 3),
            "regions": len(positives),
        })
    ranked.sort(key=lambda c: c["area"])
    return ranked


# ----- 검사 -----

def _check_size(width, height) -> None:
    for name, v in (("width", width), ("height", height)):
        if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v <= 0:
            raise ValueError(f"{name}은 1 이상의 정수여야 합니다: {v!r}")


def _parse(rle: str) -> list[int]:
    """RLE 문자열을 정수 목록으로. "-1"이면 빈 목록."""
    if not isinstance(rle, str):
        raise ValueError(f"RLE는 문자열이어야 합니다: {rle!r}")
    text = rle.strip()
    if text == NO_PNEUMOTHORAX:
        return []
    if not text:
        raise ValueError('RLE가 비어 있습니다. 기흉이 없으면 "-1"이어야 합니다.')
    try:
        numbers = [int(t) for t in text.split()]
    except ValueError:
        raise ValueError(f"RLE에 숫자가 아닌 값이 있습니다: {text[:50]}") from None
    if len(numbers) % 2:
        raise ValueError(f"RLE 숫자는 (건너뛸 칸, 기흉 칸) 쌍이라 짝수 개여야 합니다: {len(numbers)}개")
    if any(n < 0 for n in numbers):
        raise ValueError("RLE에 음수가 있습니다.")
    if any(n == 0 for n in numbers[1::2]):
        raise ValueError("RLE 구간 길이는 1 이상이어야 합니다.")
    return numbers
