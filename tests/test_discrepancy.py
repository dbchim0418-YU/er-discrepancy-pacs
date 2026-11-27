"""불일치 판정 테스트. 기준: docs/state_rules.md 5절 판정표·입력 규칙"""
import pytest

from workflow.discrepancy import compare_readings, validate_reading


def r(finding, side="none", size=None):
    """소견 dict를 짧게 만든다. 예: r("present", "left", "small")"""
    return {"finding": finding, "side": side, "size": size}


ABSENT = r("absent")


# ----- 판정표 1~9번 -----

@pytest.mark.parametrize(
    "no, prelim, final, grade, fields",
    [
        (1, ABSENT, r("present", "left", "small"), "major", ["finding"]),
        (2, ABSENT, r("suspected", "left"), "major", ["finding"]),
        (3, r("suspected", "left"), r("present", "left", "small"), "minor", ["finding"]),
        (4, r("present", "left", "small"), ABSENT, "minor", ["finding"]),
        (4, r("suspected", "right"), ABSENT, "minor", ["finding"]),
        (4, r("present", "right", "large"), r("suspected", "right"), "minor", ["finding"]),
        (5, r("present", "left", "small"), r("present", "right", "small"), "major", ["side"]),
        (5, r("suspected", "right"), r("suspected", "left"), "major", ["side"]),
        (6, r("present", "left", "small"), r("present", "both", "small"), "major", ["side"]),
        (6, r("suspected", "right"), r("present", "both", "large"), "major", ["finding", "side"]),
        (7, r("present", "both", "small"), r("present", "left", "small"), "minor", ["side"]),
        (8, r("present", "left", "small"), r("present", "left", "large"), "minor", ["size"]),
        (8, r("present", "left", "large"), r("present", "left", "small"), "minor", ["size"]),
    ],
)
def test_judgement_table(no, prelim, final, grade, fields):
    assert compare_readings(prelim, final) == {"grade": grade, "fields": fields}


@pytest.mark.parametrize(
    "reading",
    [ABSENT, r("suspected", "both"), r("present", "right", "large")],
)
def test_same_readings_match(reading):
    # 판정표 9번: 모든 값이 같으면 일치
    assert compare_readings(reading, dict(reading)) is None


def test_highest_grade_wins_and_all_fields_are_listed():
    # 좌·작음 → 우·큼 = 5번(중대) + 8번(경미) → 중대, 두 항목 모두 표시
    result = compare_readings(r("present", "left", "small"), r("present", "right", "large"))
    assert result == {"grade": "major", "fields": ["side", "size"]}


def test_side_is_not_compared_when_one_side_is_absent():
    # 없음 → 좌측 있음: 좌우 차이는 '놓침'(finding)에 이미 포함되므로 side를 따로 넣지 않는다
    assert compare_readings(ABSENT, r("present", "left", "large"))["fields"] == ["finding"]


def test_memo_and_extra_keys_are_ignored():
    prelim = {**r("present", "left", "small"), "memo": "응급의 메모"}
    final = {**r("present", "left", "small"), "memo": "다른 메모", "author_uid": "u2"}
    assert compare_readings(prelim, final) is None


# ----- 입력 검사 (잘못된 입력 7종) -----

@pytest.mark.parametrize(
    "reading, message",
    [
        (r("absent", "left"), "좌우를 선택할 수 없습니다"),
        (r("absent", "none", "small"), "크기를 선택할 수 없습니다"),
        (r("suspected", "none"), "좌우를 선택해야 합니다"),
        (r("suspected", "left", "small"), "크기를 입력하지 않습니다"),
        (r("present", "none", "small"), "좌우를 선택해야 합니다"),
        (r("present", "left"), "크기를 선택해야 합니다"),
        (r("maybe"), "허용되지 않은 값"),
        (r("present", "up", "small"), "허용되지 않은 값"),
        (r("present", "left", "huge"), "허용되지 않은 값"),
        (r("present", "left", 3), "허용되지 않은 값"),
        ({"side": "left"}, "소견\\(있음/없음/의심\\)을 선택"),
        (["present", "left", "small"], "형태"),
    ],
)
def test_bad_reading_is_rejected(reading, message):
    with pytest.raises(ValueError, match=message):
        validate_reading(reading)


def test_bad_reading_is_rejected_in_compare():
    with pytest.raises(ValueError):
        compare_readings(r("present", "left"), ABSENT)


@pytest.mark.parametrize(
    "reading, expected",
    [
        ({"finding": "absent"}, {"finding": "absent", "side": "none", "size": None}),
        ({"finding": "suspected", "side": "both"}, {"finding": "suspected", "side": "both", "size": None}),
        (
            {"finding": "present", "side": "left", "size": "small", "memo": "x"},
            {"finding": "present", "side": "left", "size": "small"},
        ),
    ],
)
def test_validate_reading_normalizes(reading, expected):
    assert validate_reading(reading) == expected
