"""불일치 탐지와 재연락 추적. 주인: 예찬

Firestore discrepancies 컬렉션 필드(개발 규칙 5번):
case_id, grade, fields, callback_status, callback_result, due_at, resolved_by, resolved_at
"""
from __future__ import annotations


def compare_readings(prelim: dict, final: dict) -> dict | None:
    """TODO(예찬): 예비·최종 소견 비교. 일치면 None, 불일치면 {"grade": "major"|"minor", "fields": [...]}."""
    raise NotImplementedError

# TODO(예찬): record_callback(), 기한 초과 목록
