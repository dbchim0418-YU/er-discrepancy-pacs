"""로그인과 권한 검사. 주인: 채민

- 1주차에는 auth_mode = "fake"로 역할만 골라 들어간다(팀원 개발용).
- Firebase 설정이 끝나면 auth_mode = "firebase"로 바꿔 실제 로그인한다.
- 화면에서 버튼을 숨기는 것과 별개로, 저장·수정 함수 첫 줄에서 require_role()로 다시 검사한다.
"""
from __future__ import annotations

import functools
from typing import Callable, Optional

import requests
import streamlit as st

from core.config import get_firebase_section, get_setting

# 역할 값 (코드·DB용 영어 값 → 화면 표시용 한글)
ROLES = {
    "er": "응급의",
    "radiologist": "판독의",
    "admin": "관리자",
}

SESSION_KEY = "auth_user"
_FIREBASE_SIGNIN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={key}"
)


# ----- 로그인 상태 -----

def get_current_user() -> Optional[dict]:
    """로그인한 사용자 {uid, email, name, role}. 로그인 전이면 None."""
    return st.session_state.get(SESSION_KEY)


def login_fake(role: str, name: str = "") -> dict:
    """임시 로그인: 역할만 골라 들어간다. 개발·시연 준비용."""
    if role not in ROLES:
        raise ValueError(f"알 수 없는 역할입니다: {role}")
    user = {
        "uid": f"fake-{role}",
        "email": f"{role}@fake.local",
        "name": name or ROLES[role],
        "role": role,
    }
    st.session_state[SESSION_KEY] = user
    return user


def login_firebase(email: str, password: str) -> dict:
    """Firebase Authentication 이메일·비밀번호 로그인.

    로그인 성공 후 Firestore users/{uid} 문서에서 역할을 읽는다.
    TODO(채민): users 문서가 없을 때 처리, 토큰 만료 처리.
    """
    from core.db import get_db  # Firebase 설정이 있을 때만 불러온다

    fb = get_firebase_section()
    if fb is None:
        raise RuntimeError("Firebase 설정이 없습니다. secrets.toml을 확인하세요.")

    resp = requests.post(
        _FIREBASE_SIGNIN_URL.format(key=fb["web_api_key"]),
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=10,
    )
    if resp.status_code != 200:
        raise PermissionError("이메일 또는 비밀번호가 올바르지 않습니다.")
    data = resp.json()

    uid = data["localId"]
    doc = get_db().collection("users").document(uid).get()
    if not doc.exists:
        raise PermissionError("등록된 역할이 없는 계정입니다. 관리자에게 문의하세요.")
    profile = doc.to_dict()

    user = {
        "uid": uid,
        "email": data.get("email", email),
        "name": profile.get("name", email),
        "role": profile.get("role"),
    }
    st.session_state[SESSION_KEY] = user
    return user


def logout() -> None:
    st.session_state.pop(SESSION_KEY, None)


def auth_mode() -> str:
    return get_setting("auth_mode")


# ----- 권한 검사 -----

def require_role(*roles: str, user: Optional[dict] = None) -> dict:
    """현재 사용자가 허용된 역할인지 검사한다.

    저장·수정 함수의 첫 줄에서 호출한다. 통과하면 사용자 정보를 돌려주고,
    로그인하지 않았거나 역할이 맞지 않으면 PermissionError를 낸다.

    예: require_role("er", "admin")
    """
    if user is None:
        user = get_current_user()
    if user is None:
        raise PermissionError("로그인이 필요합니다.")
    if roles and user.get("role") not in roles:
        allowed = ", ".join(ROLES.get(r, r) for r in roles)
        raise PermissionError(f"권한이 없습니다. 허용된 역할: {allowed}")
    return user


def role_required(*roles: str) -> Callable:
    """require_role을 함수 장식자로 쓰는 버전.

    @role_required("radiologist")
    def save_final_reading(...): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            require_role(*roles)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ----- 화면용 -----

def require_login() -> dict:
    """페이지 맨 위에서 호출. 로그인하지 않았으면 안내 후 페이지를 멈춘다."""
    user = get_current_user()
    if user is None:
        st.warning("로그인이 필요합니다. 왼쪽 메뉴의 첫 화면(app)에서 로그인하세요.")
        st.stop()
    return user
