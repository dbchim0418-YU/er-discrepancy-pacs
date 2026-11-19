"""파일 저장·삭제. 주인: 채민

경로 규칙(개발 규칙 5번):
  원본       originals/{case_id}/{image_id}.{dcm|png|jpg}
  처리 결과  results/{image_id}/{processing_id}.png
  리포트     reports/{case_id}/{report_id}.pdf

- 원본은 한 번 저장하면 덮어쓰지 않는다.
- 파일과 DB 기록이 어긋나지 않도록 save_with_record()를 쓴다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, TypeVar

from core.config import get_setting

T = TypeVar("T")


class StorageError(Exception):
    """저장 과정의 실패. 화면에 이유를 보여줄 때 쓴다."""


def _root(root: Optional[str | Path] = None) -> Path:
    return Path(root if root is not None else get_setting("storage_root")).resolve()


def _full_path(path: str, root: Optional[str | Path] = None) -> Path:
    base = _root(root)
    full = (base / path).resolve()
    if base != full and base not in full.parents:
        raise StorageError(f"허용되지 않은 저장 경로입니다: {path}")
    return full


def save_file(data: bytes, path: str, root: Optional[str | Path] = None) -> str:
    """파일을 저장하고 저장 경로(상대 경로)를 돌려준다. 같은 경로에 파일이 있으면 거절한다."""
    full = _full_path(path, root)
    if full.exists():
        raise FileExistsError(f"이미 같은 경로에 파일이 있습니다(덮어쓰기 금지): {path}")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    return path


def read_file(path: str, root: Optional[str | Path] = None) -> bytes:
    return _full_path(path, root).read_bytes()


def delete_file(path: str, root: Optional[str | Path] = None) -> None:
    full = _full_path(path, root)
    if full.exists():
        full.unlink()


def save_with_record(
    data: bytes,
    path: str,
    write_record: Callable[[str], T],
    root: Optional[str | Path] = None,
) -> T:
    """파일 저장 → DB 기록 순서로 처리하고, DB 기록이 실패하면 저장한 파일을 지운다.

    write_record: 저장 경로를 받아 DB에 기록하는 함수. 반환값을 그대로 돌려준다.
    순서를 이렇게 정한 이유: DB에 기록만 있고 파일이 없는 상태(조회 시 오류)를 막기 위해서다.
    """
    saved = save_file(data, path, root)
    try:
        return write_record(saved)
    except Exception as exc:
        delete_file(saved, root)
        raise StorageError("DB 기록에 실패해 업로드를 취소했습니다. 다시 시도해 주세요.") from exc
