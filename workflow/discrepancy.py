"""불일치 탐지와 재연락 추적. 주인: 예찬

규칙 문서: docs/state_rules.md 5절(불일치 판정), 6절(재연락)

Firestore discrepancies 컬렉션 필드(개발 규칙 5번):
case_id, grade, fields, callback_status, callback_result, due_at, resolved_by, resolved_at
"""
from __future__ import annotations

from workflow.state import (
    ABSENT,
    FINDING,
    GRADE_MAJOR,
    GRADE_MINOR,
    PRESENT,
    SIDE,
    SIDE_NONE,
    SIZE,
    SUSPECTED,
)

# 좌우 값을 "어느 쪽에 기흉이 있다고 봤는가"의 집합으로 바꾼다.
# 예: 좌 → 양쪽이면 {"left"} → {"left", "right"}, 최종에만 있는 "right"가 놓친 쪽이다.
_SIDE_SET = {
    "left": {"left"},
    "right": {"right"},
    "both": {"left", "right"},
}

# fields에 담는 순서
_FIELD_ORDER = ("finding", "side", "size")


def validate_reading(reading: dict) -> dict:
    """소견 입력을 검사하고 {"finding", "side", "size"}만 담은 dict로 돌려준다.

    소견별 입력 규칙(docs/state_rules.md 5절):
      없음(absent)      좌우 none만, 크기 입력하면 거절
      의심(suspected)   좌우 left/right/both 필수, 크기 입력하면 거절
      있음(present)     좌우 left/right/both 필수, 크기 small/large 필수

    memo 같은 다른 키는 검사하지 않고 결과에서 뺀다.
    잘못된 입력은 화면에 보여 줄 이유와 함께 ValueError로 거절한다.
    """
    if not isinstance(reading, dict):
        raise ValueError("소견은 {'finding', 'side', 'size'} 형태여야 합니다.")

    finding = reading.get("finding")
    if finding is None:
        raise ValueError("소견(있음/없음/의심)을 선택해야 합니다.")
    _check_value("finding", finding, FINDING)

    side = reading.get("side")
    size = reading.get("size")
    if side is not None:
        _check_value("side", side, SIDE)
    if size is not None:
        _check_value("size", size, SIZE)

    if finding == ABSENT:
        if side not in (None, SIDE_NONE):
            raise ValueError("기흉이 없으면 좌우를 선택할 수 없습니다.")
        if size is not None:
            raise ValueError("기흉이 없으면 크기를 선택할 수 없습니다.")
        return {"finding": ABSENT, "side": SIDE_NONE, "size": None}

    if finding == SUSPECTED:
        if side in (None, SIDE_NONE):
            raise ValueError("기흉이 의심되면 좌우를 선택해야 합니다. 어느 쪽인지 모르면 '양쪽'을 고르세요.")
        if size is not None:
            raise ValueError("의심 단계에서는 크기를 입력하지 않습니다.")
        return {"finding": SUSPECTED, "side": side, "size": None}

    # PRESENT
    if side in (None, SIDE_NONE):
        raise ValueError("기흉이 있으면 좌우를 선택해야 합니다.")
    if size is None:
        raise ValueError("기흉이 있으면 크기를 선택해야 합니다.")
    return {"finding": PRESENT, "side": side, "size": size}


def compare_readings(prelim: dict, final: dict) -> dict | None:
    """예비 소견과 최종 판독을 비교한다. (docs/state_rules.md 5절 판정표)

    일치하면 None, 다르면 {"grade": "major" | "minor", "fields": [다른 항목]}.

    한 줄 원칙: 기흉 자체를 놓쳤거나 다른 쪽을 봤으면 중대(major).
               이미 알아봤고 정도(확신·크기)만 다르거나, 더 심각하게 봤으면 경미(minor).
    여러 항목이 다르면 가장 높은 등급을 쓰고, 다른 항목은 모두 fields에 담는다.
    """
    p = validate_reading(prelim)
    f = validate_reading(final)

    grades: dict[str, str] = {}  # 다른 항목 → 그 항목의 등급

    # 1) 소견 유무 (판정표 1~4번)
    if p["finding"] != f["finding"]:
        if p["finding"] == ABSENT:
            grades["finding"] = GRADE_MAJOR      # 1번 없음→있음, 2번 없음→의심: 기흉을 놓침
        else:
            grades["finding"] = GRADE_MINOR      # 3번 의심→있음, 4번 과대 판정

    # 2) 좌우 (판정표 5~7번): 둘 다 기흉이 있거나 의심일 때만 비교한다.
    #    한쪽이 "없음"이면 좌우 차이는 이미 1)에서 판정됐다.
    if p["finding"] != ABSENT and f["finding"] != ABSENT and p["side"] != f["side"]:
        missed = _SIDE_SET[f["side"]] - _SIDE_SET[p["side"]]
        # 최종에만 있는 쪽이 있으면 그쪽을 놓친 것(5번 반대쪽, 6번 한쪽 놓침), 아니면 과대 판정(7번)
        grades["side"] = GRADE_MAJOR if missed else GRADE_MINOR

    # 3) 크기 (판정표 8번): 둘 다 "있음"일 때만 크기가 있다.
    if p["finding"] == PRESENT and f["finding"] == PRESENT and p["size"] != f["size"]:
        grades["size"] = GRADE_MINOR

    if not grades:
        return None                               # 9번 일치

    grade = GRADE_MAJOR if GRADE_MAJOR in grades.values() else GRADE_MINOR
    fields = [name for name in _FIELD_ORDER if name in grades]
    return {"grade": grade, "fields": fields}


def _check_value(name: str, value, allowed: tuple) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"허용되지 않은 값입니다: {name}={value!r} (가능한 값: {', '.join(allowed)})")


# TODO(예찬): record_callback(), 기한 초과 목록 (재연락 기한은 회의 확정 후, DB 함수가 나온 뒤 구현)
