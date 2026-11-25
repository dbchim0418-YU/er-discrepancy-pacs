"""홈: 로그인과 로그인 후 안내. 주인: 채민"""
import streamlit as st

from core.auth import ROLES, auth_mode, get_current_user, login_fake, login_firebase, logout

st.title("응급실 판독 불일치 관리 PACS")
st.caption("교육용 프로토타입, 모의 케이스만 사용, 실제 진단 목적이 아님")

user = get_current_user()

if user is None:
    st.subheader("로그인")
    if auth_mode() == "firebase":
        with st.form("auth_login_form"):
            email = st.text_input("이메일")
            password = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인"):
                try:
                    login_firebase(email, password)
                    st.rerun()  # 역할에 맞는 메뉴로 다시 그리기
                except Exception as exc:
                    st.error(str(exc))
    else:
        st.info("임시 로그인 모드입니다. 역할을 골라 들어가세요. (Firebase 연결 전 개발용)")
        with st.form("auth_fake_form"):
            role = st.selectbox("역할", list(ROLES), format_func=lambda r: f"{ROLES[r]} ({r})")
            name = st.text_input("이름(선택)")
            if st.form_submit_button("로그인"):
                login_fake(role, name)
                st.rerun()  # 역할에 맞는 메뉴로 다시 그리기
else:
    st.success(f"{user['name']} 님 {ROLES.get(user['role'], user['role'])} 권한으로 로그인했습니다.")
    if st.button("로그아웃", key="auth_logout"):
        logout()
        st.rerun()

    st.markdown(
        """
        **왼쪽 메뉴**
        - 케이스: 케이스 등록·검색, 영상 업로드와 보기
        - 영상처리: 흉막선 강조 보기, ROI 분석
        - 판독: 예비·최종 판독 입력, 불일치 확인
        - 관리자: 담당자 배정, 재연락 현황 (관리자만)
        """
    )
