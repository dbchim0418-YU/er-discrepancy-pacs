"""Firestore 연결. 주인: 채민

Firebase 설정이 없으면 get_db()는 None을 돌려준다(가짜 로그인으로 개발할 때).
컬렉션·필드 이름은 개발 규칙 5번을 따른다:
users, cases, images, processing, readings, discrepancies
"""
from __future__ import annotations

import streamlit as st

from core.config import get_firebase_section


@st.cache_resource(show_spinner=False)
def get_db():
    """Firestore 클라이언트. 설정이 없으면 None."""
    fb = get_firebase_section()
    if fb is None or "service_account" not in fb:
        return None

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(fb["service_account"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()


def is_db_ready() -> bool:
    return get_db() is not None

# TODO(채민): 공통 읽기·쓰기 함수 (create_case, get_case, list_cases, add_image_record 등)
