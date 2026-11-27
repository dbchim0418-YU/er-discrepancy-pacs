"""케이스 상태와 전환 규칙. 주인: 예찬

규칙 문서: docs/state_rules.md (2절 상태 전이도, 3절 전환표, 4절 권한)
다른 사람은 이 파일의 상수를 가져다 쓴다. (문자열을 직접 입력하지 않는다)

구조 (PR #7 리뷰에서 합의)
- 사람이 하는 전환: check_transition() / can_transition()으로 검사한다. 화면용 change_state()가 쓴다.
- 시스템이 하는 전환(불일치 판정 결과): judged_state() / rejudged_state()로 다음 상태를 계산한다.
  최종 판독 저장·수정 함수 안에서만 쓴다. 사람이 이 전환을 요청하면 check_transition()이 거절한다.
"""
from __future__ import annotations

from typing import Callable, Optional

from core.auth import ROLES, require_role

# ----- 케이스 상태 -----
RECEIVED = "RECEIVED"                    # 접수
PRELIM_DONE = "PRELIM_DONE"              # 예비 판독 완료
FINAL_IN_PROGRESS = "FINAL_IN_PROGRESS"  # 최종 판독 중
FINAL_DONE = "FINAL_DONE"                # 최종 판독 완료
NEEDS_REVIEW = "NEEDS_REVIEW"            # 확인 필요(경미 불일치)
NEEDS_CALLBACK = "NEEDS_CALLBACK"        # 재연락 필요(중대 불일치)
CALLBACK_DONE = "CALLBACK_DONE"          # 재연락 완료
CLOSED = "CLOSED"                        # 종료

STATE_LABELS = {
    RECEIVED: "접수",
    PRELIM_DONE: "예비 판독 완료",
    FINAL_IN_PROGRESS: "최종 판독 중",
    FINAL_DONE: "최종 판독 완료",
    NEEDS_REVIEW: "확인 필요",
    NEEDS_CALLBACK: "재연락 필요",
    CALLBACK_DONE: "재연락 완료",
    CLOSED: "종료",
}

# ----- 소견 값 -----
ABSENT, SUSPECTED, PRESENT = "absent", "suspected", "present"
SIDE_NONE = "none"
GRADE_MAJOR, GRADE_MINOR = "major", "minor"

FINDING = (PRESENT, ABSENT, SUSPECTED)
SIDE = ("left", "right", "both", SIDE_NONE)
SIZE = ("small", "large")
GRADE = (GRADE_MAJOR, GRADE_MINOR)
CALLBACK_RESULT = ("reached", "no_answer", "revisit")

# 재연락 결과 중 케이스를 "재연락 완료"로 넘기는 값. no_answer(부재)는 상태를 바꾸지 않는다.
CALLBACK_DONE_RESULTS = ("reached", "revisit")

# 최종 판독을 수정할 수 있는(= 다시 판정하는) 상태
REJUDGE_STATES = (FINAL_DONE, NEEDS_REVIEW, NEEDS_CALLBACK, CALLBACK_DONE, CLOSED)


# ----- 사람이 하는 전환 (docs/state_rules.md 3절 전환표) -----
# (현재 상태, 다음 상태) → (허용 역할, 추가 조건 검사 함수)
# 검사 함수는 (case, user, payload)를 받아 통과하면 None, 막으면 이유 문구를 돌려준다.

def _needs_image_and_prelim(case: dict, user: dict, payload: dict) -> Optional[str]:
    if case.get("image_count", 0) < 1:
        return "영상을 1장 이상 등록해야 예비 판독을 완료할 수 있습니다."
    return _valid_reading(payload.get("prelim"), "예비 소견")


def _needs_assigned_radiologist(case: dict, user: dict, payload: dict) -> Optional[str]:
    assigned = case.get("assigned_radiologist_uid")
    if not assigned:
        return "아직 담당 판독의가 배정되지 않았습니다. 관리자에게 배정을 요청하세요."
    if assigned != user.get("uid"):
        return "이 케이스의 담당 판독의가 아닙니다."
    return None


def _needs_assigned_and_final(case: dict, user: dict, payload: dict) -> Optional[str]:
    return _needs_assigned_radiologist(case, user, payload) or _valid_reading(payload.get("final"), "최종 판독")


def _needs_review_memo(case: dict, user: dict, payload: dict) -> Optional[str]:
    memo = payload.get("memo")
    if not isinstance(memo, str) or not memo.strip():
        return "확인 메모를 작성해야 종료할 수 있습니다."
    return None


def _needs_callback_result(case: dict, user: dict, payload: dict) -> Optional[str]:
    result = payload.get("callback_result")
    if result == "no_answer":
        return "부재는 재연락 완료가 아닙니다. 시도 기록만 남기고 다시 연락해야 합니다."
    if result not in CALLBACK_DONE_RESULTS:
        return "재연락 결과(연락 완료 또는 재내원 예약)를 기록해야 합니다."
    return None


_HUMAN_TRANSITIONS: dict[tuple[str, str], tuple[tuple[str, ...], Optional[Callable]]] = {
    (RECEIVED, PRELIM_DONE): (("er",), _needs_image_and_prelim),
    (PRELIM_DONE, FINAL_IN_PROGRESS): (("radiologist",), _needs_assigned_radiologist),
    (FINAL_IN_PROGRESS, FINAL_DONE): (("radiologist",), _needs_assigned_and_final),
    (NEEDS_REVIEW, CLOSED): (("er",), _needs_review_memo),
    (NEEDS_CALLBACK, CALLBACK_DONE): (("er",), _needs_callback_result),
    (CALLBACK_DONE, CLOSED): (("admin",), None),
}


def check_transition(case: dict, to_state: str, user: Optional[dict], payload: Optional[dict] = None) -> Optional[str]:
    """사람이 요청한 상태 전환을 검사한다. 허용되면 None, 막히면 화면에 보여 줄 이유 문구.

    case     케이스 정보. 사용하는 키: state(필수), assigned_radiologist_uid, image_count
    to_state 바꾸려는 상태
    user     로그인한 사용자 {uid, role, ...}
    payload  전환에 필요한 입력. 예비 판독 완료 {"prelim": 소견}, 최종 판독 완료 {"final": 소견},
             확인 필요 → 종료 {"memo": 확인 메모}, 재연락 {"callback_result": 결과}
    """
    payload = payload or {}
    current = case.get("state")

    if current not in STATE_LABELS:
        return f"케이스 상태를 알 수 없습니다: {current!r}"
    if to_state not in STATE_LABELS:
        return f"알 수 없는 상태입니다: {to_state!r}"
    if current == to_state:
        # 버튼을 두 번 누른 경우. 실제 DB 저장에서는 트랜잭션으로 한 번 더 막는다(3절).
        return "이미 처리된 요청입니다."

    rule = _HUMAN_TRANSITIONS.get((current, to_state))
    if rule is None:
        return _rejection_reason(current, to_state)

    roles, extra_check = rule
    try:
        require_role(*roles, user=user)
    except PermissionError as exc:
        return str(exc)

    if extra_check is not None:
        return extra_check(case, user, payload)
    return None


def can_transition(case: dict, to_state: str, user: Optional[dict], payload: Optional[dict] = None) -> bool:
    """check_transition()의 결과를 참·거짓으로만 돌려준다. (버튼을 보여 줄지 정할 때)"""
    return check_transition(case, to_state, user, payload) is None


# ----- 시스템이 하는 전환 (불일치 판정 결과) -----

def judged_state(grade: Optional[str]) -> str:
    """판정 결과에 따른 다음 상태. 일치(None) → 종료, 경미 → 확인 필요, 중대 → 재연락 필요."""
    if grade is None:
        return CLOSED
    if grade == GRADE_MINOR:
        return NEEDS_REVIEW
    if grade == GRADE_MAJOR:
        return NEEDS_CALLBACK
    raise ValueError(f"알 수 없는 판정 등급입니다: {grade!r}")


def rejudged_state(current_state: str, grade: Optional[str]) -> str:
    """최종 판독을 수정한 뒤 다시 판정했을 때의 다음 상태. (docs/state_rules.md 2절)

    최종 판독이 끝난 상태에서만 수정할 수 있다. 종료된 케이스도 새로 불일치가 생기면 다시 열린다.
    """
    if current_state not in REJUDGE_STATES:
        raise ValueError(f"'{STATE_LABELS.get(current_state, current_state)}' 상태에서는 최종 판독을 수정할 수 없습니다.")
    return judged_state(grade)


def change_state(case_id: str, to_state: str, user: dict, payload: Optional[dict] = None) -> tuple[bool, str]:
    """TODO(예찬): 화면용 상태 변경. 사람 전환만 허용한다(PR #7 리뷰 합의).

    Firestore 트랜잭션 안에서 케이스를 다시 읽고 check_transition()으로 검사한 뒤 바꾸고,
    cases/{caseId}/history에 (이전 상태, 다음 상태, 실행자, 시각(UTC), 이유)를 남긴다.
    채민의 DB 함수가 나온 뒤 구현한다.
    """
    raise NotImplementedError


# ----- 내부 도우미 -----

def _valid_reading(reading, label: str) -> Optional[str]:
    from workflow.discrepancy import validate_reading  # 서로 import하므로 함수 안에서 불러온다

    if reading is None:
        return f"{label}을 입력해야 합니다."
    try:
        validate_reading(reading)
    except ValueError as exc:
        return f"{label}: {exc}"
    return None


def _rejection_reason(current: str, to_state: str) -> str:
    """전환표에 없는 전환을 막을 때의 이유 문구."""
    if current == RECEIVED and to_state in (FINAL_IN_PROGRESS, FINAL_DONE):
        return "예비 판독 없이 최종 판독을 진행할 수 없습니다."
    if current == FINAL_DONE or to_state in (NEEDS_REVIEW, NEEDS_CALLBACK):
        return "판정 결과에 따른 전환은 시스템만 수행합니다."
    if current == NEEDS_CALLBACK and to_state == CLOSED:
        return "재연락 결과를 기록해야 종료할 수 있습니다."
    return (
        f"'{STATE_LABELS[current]}'에서 '{STATE_LABELS[to_state]}'(으)로 바꿀 수 없습니다."
    )


# 역할 값이 core.auth와 어긋나지 않았는지 불러올 때 확인한다. (python -O에서도 빠지지 않도록 assert 대신 raise)
_unknown_roles = {r for roles, _ in _HUMAN_TRANSITIONS.values() for r in roles} - set(ROLES)
if _unknown_roles:
    raise RuntimeError(f"전환표에 core.auth.ROLES에 없는 역할이 있습니다: {_unknown_roles}")
