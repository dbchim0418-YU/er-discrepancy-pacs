"""담당자 배정, 재연락 현황, 대시보드. 주인: 예찬"""
import streamlit as st

from core.auth import require_login, require_role

user = require_login()
st.title("관리자")

try:
    require_role("admin", user=user)
except PermissionError as exc:
    st.error(str(exc))
    st.stop()

st.info("TODO(예찬): 담당자 배정, 불일치·재연락 현황, 기한 초과 경고")
