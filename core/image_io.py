"""영상 읽기. 주인: 채민

모든 영상을 흑백 uint8(0~255) NumPy 배열로 바꾸는 곳은 이 파일 하나뿐이다(개발 규칙 2번).
뷰어와 알고리즘은 load_image()가 돌려준 배열만 쓴다.

DICOM 변환 순서: 픽셀 읽기 → Rescale Slope/Intercept → windowing → MONOCHROME1이면 반전 → 0~255
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import numpy as np

SUPPORTED_FORMATS = {
    ".dcm": "dicom",
    ".dicom": "dicom",
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
}

Source = Union[str, Path, bytes]


class ImageFormatError(ValueError):
    """지원하지 않거나 읽을 수 없는 파일. 메시지를 화면에 그대로 보여준다."""


def detect_format(filename: str) -> str:
    """파일 이름의 확장자로 형식을 판단한다. 지원하지 않으면 ImageFormatError."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        allowed = ", ".join(sorted(SUPPORTED_FORMATS))
        raise ImageFormatError(f"지원하지 않는 형식입니다({ext or '확장자 없음'}). 지원 형식: {allowed}")
    return SUPPORTED_FORMATS[ext]


def load_image(source: Source, filename: str | None = None) -> tuple[np.ndarray, dict]:
    """영상을 읽어 (흑백 uint8 배열, 메타데이터 dict)를 돌려준다.

    source: 파일 경로 또는 바이트(업로드한 파일 내용)
    filename: source가 바이트일 때 형식 판단용 파일 이름
    """
    if isinstance(source, (str, Path)):
        filename = filename or str(source)
        data = Path(source).read_bytes()
    else:
        data = source
        if filename is None:
            raise ValueError("바이트로 읽을 때는 filename이 필요합니다.")

    fmt = detect_format(filename)
    try:
        if fmt == "dicom":
            image, meta = _load_dicom(data)
        else:
            image, meta = _load_raster(data)
    except ImageFormatError:
        raise
    except Exception as exc:
        raise ImageFormatError(f"파일을 읽을 수 없습니다. 손상되었거나 형식이 다릅니다. ({exc})") from exc

    meta["format"] = fmt
    meta["height"], meta["width"] = image.shape
    return image, meta


# ----- DICOM -----

def _first(value):
    """DICOM 다중값(MultiValue)이면 첫 값을 쓴다."""
    try:
        return float(value[0])
    except (TypeError, IndexError):
        return float(value)


def _load_dicom(data: bytes) -> tuple[np.ndarray, dict]:
    import pydicom

    ds = pydicom.dcmread(io.BytesIO(data))
    if "PixelData" not in ds:
        raise ImageFormatError("영상 픽셀이 없는 DICOM입니다(예: 보고서·윤곽 객체).")

    arr = ds.pixel_array.astype(np.float32)
    photometric = str(getattr(ds, "PhotometricInterpretation", "MONOCHROME2"))
    frames = int(getattr(ds, "NumberOfFrames", 1) or 1)

    # 여러 프레임이면 첫 프레임, 컬러면 흑백으로
    if frames > 1:
        arr = arr[0]
    if arr.ndim == 3:
        arr = arr[..., :3].mean(axis=-1)

    # 저장값 → 실제 값 (CT는 HU)
    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    arr = arr * slope + intercept

    # windowing: 헤더 값이 있으면 쓰고, 없으면 최솟값~최댓값
    center = getattr(ds, "WindowCenter", None)
    width = getattr(ds, "WindowWidth", None)
    if center is not None and width is not None and _first(width) > 0:
        c, w = _first(center), _first(width)
        low, high = c - w / 2, c + w / 2
    else:
        low, high = float(arr.min()), float(arr.max())
    image = _to_uint8(arr, low, high)

    # MONOCHROME1은 값이 클수록 어둡게 보여야 하므로 반전
    if photometric == "MONOCHROME1":
        image = 255 - image

    meta = {
        "modality": str(getattr(ds, "Modality", "")),
        "body_part": str(getattr(ds, "BodyPartExamined", "")),
        "view_position": str(getattr(ds, "ViewPosition", "")),
        "photometric": photometric,
        "frames": frames,
        "pixel_spacing": [float(v) for v in getattr(ds, "PixelSpacing", [])] or None,
        "window": [low, high],
    }
    return image, meta


# ----- PNG / JPEG -----

def _load_raster(data: bytes) -> tuple[np.ndarray, dict]:
    from PIL import Image

    with Image.open(io.BytesIO(data)) as im:
        image = np.asarray(im.convert("L"), dtype=np.uint8).copy()
    return image, {}


# ----- 공통 -----

def _to_uint8(arr: np.ndarray, low: float, high: float) -> np.ndarray:
    if high <= low:
        return np.zeros(arr.shape, dtype=np.uint8)
    scaled = (np.clip(arr, low, high) - low) / (high - low) * 255.0
    return np.round(scaled).astype(np.uint8)


def to_png_bytes(image: np.ndarray) -> bytes:
    """uint8 배열을 PNG 바이트로. 처리 결과 저장용."""
    from PIL import Image

    buf = io.BytesIO()
    Image.fromarray(image).save(buf, format="PNG")
    return buf.getvalue()
