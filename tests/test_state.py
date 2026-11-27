"""상태 전환 테스트. 기준: docs/state_rules.md 3절 전환표, 4절 권한"""
import pytest

from workflow import state as S
from workflow.state import can_transition, check_transition, judged_state, rejudged_state

ER = {"uid": "er-1", "role": "er"}
RAD = {"uid": "rad-1", "role": "radiologist"}
OTHER_RAD = {"uid": "rad-2", "role": "radiologist"}
ADMIN = {"uid": "admin-1", "role": "admin"}

PRELIM = {"finding": "absent"}
FINAL = {"finding": "present", "side": "left", "size": "small"}


def case(state, **extra):
    return {"state": state, "image_count": 1, "assigned_radiologist_uid": "rad-1", **extra}


# ----- 허용되는 전환 (전환표 그대로) -----

@pytest.mark.parametrize(
    "current, to_state, user, payload",
    [
        (S.RECEIVED, S.PRELIM_DONE, ER, {"prelim": PRELIM}),
        (S.PRELIM_DONE, S.FINAL_IN_PROGRESS, RAD, None),
        (S.FINAL_IN_PROGRESS, S.FINAL_DONE, RAD, {"final": FINAL}),
        (S.NEEDS_REVIEW, S.CLOSED, ER, {"memo": "확인했습니다"}),
        (S.NEEDS_CALLBACK, S.CALLBACK_DONE, ER, {"callback_result": "reached"}),
        (S.NEEDS_CALLBACK, S.CALLBACK_DONE, ER, {"callback_result": "revisit"}),
        (S.CALLBACK_DONE, S.CLOSED, ADMIN, None),
    ],
)
def test_allowed_transitions(current, to_state, user, payload):
    assert check_transition(case(current), to_state, user, payload) is None
    assert can_transition(case(current), to_state, user, payload)


# ----- 허용되지 않은 전환 (3절 거절 예시) -----

@pytest.mark.parametrize(
    "current, to_state, user, payload, message",
    [
        # 예비 판독 없이 최종 판독 완료
        (S.RECEIVED, S.FINAL_DONE, RAD, {"final": FINAL}, "예비 판독 없이"),
        # 응급의가 최종 판독 저장
        (S.FINAL_IN_PROGRESS, S.FINAL_DONE, ER, {"final": FINAL}, "권한이 없습니다"),
        # 사람이 판정 결과 전환을 시도
        (S.FINAL_DONE, S.CLOSED, ADMIN, None, "시스템만"),
        (S.FINAL_DONE, S.NEEDS_CALLBACK, RAD, None, "시스템만"),
        # 재연락 기록 없이 종료
        (S.NEEDS_CALLBACK, S.CLOSED, ADMIN, None, "재연락 결과를 기록해야"),
        # 같은 전환 연속 실행
        (S.PRELIM_DONE, S.PRELIM_DONE, ER, {"prelim": PRELIM}, "이미 처리된 요청"),
        # 표에 없는 되돌리기
        (S.CLOSED, S.RECEIVED, ADMIN, None, "바꿀 수 없습니다"),
    ],
)
def test_rejected_transitions(current, to_state, user, payload, message):
    reason = check_transition(case(current), to_state, user, payload)
    assert reason is not None and message in reason
    assert not can_transition(case(current), to_state, user, payload)


# ----- 역할·담당자 -----

@pytest.mark.parametrize(
    "current, to_state, user, payload",
    [
        (S.RECEIVED, S.PRELIM_DONE, RAD, {"prelim": PRELIM}),          # 예비 소견은 응급의만
        (S.RECEIVED, S.PRELIM_DONE, ADMIN, {"prelim": PRELIM}),
        (S.PRELIM_DONE, S.FINAL_IN_PROGRESS, ER, None),                # 판독 시작은 판독의만
        (S.NEEDS_REVIEW, S.CLOSED, ADMIN, {"memo": "확인"}),           # 확인 메모는 응급의만
        (S.NEEDS_CALLBACK, S.CALLBACK_DONE, ADMIN, {"callback_result": "reached"}),
        (S.CALLBACK_DONE, S.CLOSED, ER, None),                         # 종료 확인은 관리자만
    ],
)
def test_wrong_role_is_rejected(current, to_state, user, payload):
    assert "권한이 없습니다" in check_transition(case(current), to_state, user, payload)


def test_not_logged_in_is_rejected():
    assert "로그인이 필요합니다" in check_transition(case(S.CALLBACK_DONE), S.CLOSED, None)


def test_only_assigned_radiologist_can_start_and_finish():
    assert "담당 판독의가 아닙니다" in check_transition(case(S.PRELIM_DONE), S.FINAL_IN_PROGRESS, OTHER_RAD)
    assert "담당 판독의가 아닙니다" in check_transition(
        case(S.FINAL_IN_PROGRESS), S.FINAL_DONE, OTHER_RAD, {"final": FINAL}
    )


def test_unassigned_case_cannot_start():
    c = case(S.PRELIM_DONE, assigned_radiologist_uid=None)
    assert "배정되지 않았습니다" in check_transition(c, S.FINAL_IN_PROGRESS, RAD)


# ----- 전환에 필요한 입력 -----

def test_prelim_needs_image():
    c = case(S.RECEIVED, image_count=0)
    assert "영상을 1장 이상" in check_transition(c, S.PRELIM_DONE, ER, {"prelim": PRELIM})


@pytest.mark.parametrize(
    "payload, message",
    [
        (None, "예비 소견을 입력해야"),
        ({"prelim": {"finding": "present", "side": "left"}}, "크기를 선택해야"),
    ],
)
def test_prelim_needs_valid_reading(payload, message):
    assert message in check_transition(case(S.RECEIVED), S.PRELIM_DONE, ER, payload)


def test_final_needs_valid_reading():
    reason = check_transition(case(S.FINAL_IN_PROGRESS), S.FINAL_DONE, RAD, {"final": {"finding": "suspected"}})
    assert "좌우를 선택해야" in reason


@pytest.mark.parametrize("memo", [None, "", "   "])
def test_review_close_needs_memo(memo):
    assert "확인 메모" in check_transition(case(S.NEEDS_REVIEW), S.CLOSED, ER, {"memo": memo})


def test_no_answer_does_not_finish_callback():
    reason = check_transition(case(S.NEEDS_CALLBACK), S.CALLBACK_DONE, ER, {"callback_result": "no_answer"})
    assert "부재" in reason


def test_callback_needs_result():
    assert "재연락 결과" in check_transition(case(S.NEEDS_CALLBACK), S.CALLBACK_DONE, ER, {})


# ----- 잘못된 상태 값 -----

def test_unknown_states_are_rejected():
    assert "알 수 없는 상태" in check_transition(case(S.RECEIVED), "DONE", ER)
    assert "상태를 알 수 없습니다" in check_transition({"state": "??"}, S.PRELIM_DONE, ER)


# ----- 시스템 전환: 판정 결과 → 다음 상태 -----

@pytest.mark.parametrize(
    "grade, expected",
    [(None, S.CLOSED), ("minor", S.NEEDS_REVIEW), ("major", S.NEEDS_CALLBACK)],
)
def test_judged_state(grade, expected):
    assert judged_state(grade) == expected


def test_judged_state_rejects_unknown_grade():
    with pytest.raises(ValueError):
        judged_state("critical")


def test_rejudge_reopens_closed_case():
    # 종료된 케이스도 최종 판독 수정으로 중대 불일치가 생기면 다시 열린다
    assert rejudged_state(S.CLOSED, "major") == S.NEEDS_CALLBACK
    assert rejudged_state(S.NEEDS_CALLBACK, None) == S.CLOSED


@pytest.mark.parametrize("current", [S.RECEIVED, S.PRELIM_DONE, S.FINAL_IN_PROGRESS])
def test_rejudge_only_after_final(current):
    with pytest.raises(ValueError, match="수정할 수 없습니다"):
        rejudged_state(current, "major")
