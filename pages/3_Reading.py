"""예비·최종 판독 입력, 불일치 확인. 주인: 예찬

세션 키 접두어: read_, disc_
"""
import streamlit as st

from core.auth import require_login

require_login()
st.title("판독")
st.info("TODO(예찬): 예비 소견(응급의) / 최종 판독(판독의) 입력, 불일치 결과 표시")
