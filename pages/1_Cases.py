"""케이스 등록·검색, 영상 업로드와 보기. 주인: 채민"""
import streamlit as st

from core.auth import require_login, require_role
from core.image_io import SUPPORTED_FORMATS, ImageFormatError, load_image
from core.viewer import show_image

user = require_login()
st.title("케이스")

tab_list, tab_new, tab_view = st.tabs(["목록·검색", "케이스 등록", "영상 열어보기"])

with tab_list:
    st.info("TODO(채민): 케이스 ID·날짜·상태·담당자로 검색·필터")

with tab_new:
    st.info("TODO(채민): 케이스 등록(모의 환자 ID, 검사 정보, 등록일) + 영상 업로드·저장")
    try:
        require_role("er", "admin", user=user)
    except PermissionError as exc:
        st.warning(str(exc))

with tab_view:
    st.caption("업로드한 파일을 저장하지 않고 열어보기만 합니다. (load_image·뷰어 시험용)")
    exts = sorted({e.lstrip(".") for e in SUPPORTED_FORMATS})
    uploaded = st.file_uploader("영상 파일", type=exts, key="case_view_upload")
    if uploaded is not None:
        try:
            image, meta = load_image(uploaded.getvalue(), filename=uploaded.name)
        except ImageFormatError as exc:
            st.error(str(exc))
        else:
            show_image(image, key="img_case_view")
            with st.expander("영상 정보"):
                st.json(meta)
