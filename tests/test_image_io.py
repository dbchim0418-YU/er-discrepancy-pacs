import io

import numpy as np
import pytest
from PIL import Image

from core.image_io import ImageFormatError, detect_format, load_image


def _png_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _dicom_bytes(pixels: np.ndarray, photometric: str = "MONOCHROME2") -> bytes:
    """테스트용 최소 DICOM(16비트 흑백)을 메모리에서 만든다."""
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = meta
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.Modality = "DX"
    ds.Rows, ds.Columns = pixels.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = photometric
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.PixelData = pixels.astype(np.uint16).tobytes()

    buf = io.BytesIO()
    ds.save_as(buf, enforce_file_format=True)
    return buf.getvalue()


def test_unsupported_extension_is_rejected():
    with pytest.raises(ImageFormatError, match="지원하지 않는 형식"):
        detect_format("report.pdf")


def test_png_becomes_uint8_gray():
    rgb = np.zeros((4, 5, 3), dtype=np.uint8)
    image, meta = load_image(_png_bytes(rgb), filename="a.png")
    assert image.dtype == np.uint8 and image.shape == (4, 5)
    assert meta["format"] == "png"


def test_broken_file_is_rejected():
    with pytest.raises(ImageFormatError, match="읽을 수 없습니다"):
        load_image(b"not an image", filename="a.png")


def test_dicom_is_scaled_to_0_255():
    pixels = np.array([[0, 1000], [2000, 4000]])
    image, meta = load_image(_dicom_bytes(pixels), filename="a.dcm")
    assert image.dtype == np.uint8
    assert image.min() == 0 and image.max() == 255
    assert meta["format"] == "dicom" and meta["modality"] == "DX"


def test_monochrome1_is_inverted():
    # MONOCHROME1은 값이 작을수록 밝게 보여야 한다
    pixels = np.array([[0, 4000]])
    mono2, _ = load_image(_dicom_bytes(pixels, "MONOCHROME2"), filename="a.dcm")
    mono1, _ = load_image(_dicom_bytes(pixels, "MONOCHROME1"), filename="b.dcm")
    assert mono2[0, 0] == 0 and mono2[0, 1] == 255
    assert mono1[0, 0] == 255 and mono1[0, 1] == 0


def test_first_handles_string_and_multivalue():
    # 리뷰 반영: "40"이 4.0이 되던 문제
    from core.image_io import _first
    assert _first("40") == 40.0
    assert _first(["40", "400"]) == 40.0
    assert _first(1500) == 1500.0
