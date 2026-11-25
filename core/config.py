"""앱 설정 읽기. 주인: 채민

설정은 `.streamlit/secrets.toml`에서 읽는다. 파일이 없거나 값이 비어 있으면 기본값을 쓴다.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

DEFAULTS = {
    "auth_mode": "fake",          # "fake" | "firebase"
    "storage_root": "data/storage",
}


def get_setting(name: str) -> Any:
    """[app] 섹션의 설정값. 없으면 DEFAULTS 값을 돌려준다."""
    try:
        return st.secrets["app"][name]
    except Exception:  # secrets.toml이 없거나 키가 없을 때
        return DEFAULTS.get(name)


def get_firebase_section() -> dict | None:
    """[firebase] 섹션 전체. 설정이 안 되어 있으면 None."""
    try:
        section = st.secrets["firebase"]
        if not section.get("web_api_key"):
            return None
        return dict(section)
    except Exception:
        return None
