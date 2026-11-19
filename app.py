"""앱 진입점: 페이지 설정과 역할별 메뉴. 주인: 채민

실행: streamlit run app.py

- 메뉴에 보이는 이름·아이콘은 여기서 정한다(파일 이름은 영어 그대로).
- 역할마다 보이는 메뉴가 다르다. 메뉴를 숨기는 것과 별개로,
  각 화면과 저장 함수의 require_role() 권한 검사는 그대로 유지한다.
"""
import streamlit as st

from core.auth import get_current_user

st.set_page_config(page_title="응급실 판독 불일치 관리 PACS", page_icon="❤️‍🩹", layout="wide")

home = st.Page("pages/0_Home.py", title="홈", icon=":material/home:", default=True)
cases = st.Page("pages/1_Cases.py", title="케이스", icon=":material/folder_open:")
imaging = st.Page("pages/2_Imaging.py", title="영상처리", icon=":material/image_search:")
reading = st.Page("pages/3_Reading.py", title="판독", icon=":material/edit_note:")
admin = st.Page("pages/4_Admin.py", title="관리자", icon=":material/admin_panel_settings:")

# 역할별 메뉴 (개발 규칙 3번 권한표 기준). 로그인 전에는 홈만 보인다.
MENU_BY_ROLE = {
    "er": [home, cases, imaging, reading],
    "radiologist": [home, cases, imaging, reading],
    "admin": [home, cases, imaging, reading, admin],
}

user = get_current_user()
menu = MENU_BY_ROLE.get(user["role"], [home]) if user else [home]

st.navigation(menu).run()