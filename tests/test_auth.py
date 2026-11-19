import pytest

from core.auth import require_role

ER = {"uid": "u1", "email": "er@test", "name": "응급의", "role": "er"}
RAD = {"uid": "u2", "email": "rad@test", "name": "판독의", "role": "radiologist"}


def test_allowed_role_passes():
    assert require_role("er", "admin", user=ER) == ER


def test_other_role_is_rejected():
    with pytest.raises(PermissionError, match="권한이 없습니다"):
        require_role("radiologist", user=ER)


def test_er_cannot_write_final_reading():
    # 권한표: 최종 판독은 판독의만
    with pytest.raises(PermissionError):
        require_role("radiologist", user=ER)
    assert require_role("radiologist", user=RAD) == RAD
