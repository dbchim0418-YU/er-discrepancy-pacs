"""흉막선 강조 보기, ROI 분석, 원본/결과 비교. 주인: 주연

사용할 공통 함수:
- core.image_io.load_image()  → uint8 배열
- core.viewer.show_image(image, key, compare=결과)  → 나란히 비교
- imaging.algorithms.process(image, params)
세션 키 접두어: proc_, roi_
"""
import streamlit as st

from core.auth import require_login

require_login()
st.title("영상처리")
st.info("TODO(주연): 알고리즘 선택·파라미터 조절, 강조 보기, ROI 통계·히스토그램")
