"""케이스 상태와 전환 규칙. 주인: 예찬

아래 값은 개발 규칙 4번 초안이다. 확정·수정은 예찬이 하고, 다른 사람은 이 상수를 가져다 쓴다.
(문자열을 직접 입력하지 않는다)
"""
from __future__ import annotations

# 케이스 상태
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

# 소견 값
FINDING = ("present", "absent", "suspected")
SIDE = ("left", "right", "both", "none")
SIZE = ("small", "large")
GRADE = ("major", "minor")
CALLBACK_RESULT = ("reached", "no_answer", "revisit")


def can_transition(case: dict, to_state: str, role: str) -> bool:
    """TODO(예찬): 허용된 전환인지 검사(현재 상태, 목표 상태, 역할)."""
    raise NotImplementedError


def change_state(case_id: str, to_state: str) -> tuple[bool, str]:
    """TODO(예찬): 상태 변경 + 이력 기록. (성공 여부, 이유)를 돌려준다."""
    raise NotImplementedError
