"""처리 이력 저장·조회. 주인: 주연

Firestore processing 컬렉션 필드(개발 규칙 5번):
processing_id, image_id, algorithm, version, params, roi, stats, result_path, run_by, run_at
처리 결과 파일은 core.storage.save_with_record()로 저장한다.
"""
from __future__ import annotations


def save_processing(image_id: str, algorithm: str, params: dict, roi: dict | None,
                    stats: dict | None, result_png: bytes) -> str:
    """TODO(주연): 결과 파일 저장 + 이력 기록, 연속 실행 중복 기록 방지. processing_id를 돌려준다."""
    raise NotImplementedError


def get_processing_history(image_id: str) -> list[dict]:
    """TODO(주연): 영상의 처리 이력 목록(최신순). 예찬의 요약 리포트에서 사용."""
    raise NotImplementedError
