# er-discrepancy-pacs

응급실 예비·최종 판독 불일치를 감지하고 재연락까지 추적하는 교육용 웹 PACS (Streamlit · Firebase)

> 교육용 프로토타입입니다. 공개 데이터와 모의 케이스만 사용하며, 분석 결과는 실제 진단이나 임상 성능을 뜻하지 않습니다.

## 폴더 구조와 파일 주인

| 경로 | 주인 | 내용 |
| --- | --- | --- |
| `app.py` | 채민 | 진입점: 페이지 설정, 역할별 메뉴(한글 이름·아이콘) |
| `pages/0_Home.py` | 채민 | 홈: 로그인, 로그인 후 안내 |
| `core/` | 채민 | 권한, Firestore, 파일 저장, 영상 읽기, 뷰어 |
| `imaging/` | 주연 | 알고리즘, ROI, RLE 마스크, 처리 이력 |
| `workflow/` | 예찬 | 상태 전이, 판독, 불일치·재연락, 요약 리포트 |
| `pages/1_Cases.py` | 채민 | 케이스 등록·검색, 영상 보기 |
| `pages/2_Imaging.py` | 주연 | 강조 보기, ROI |
| `pages/3_Reading.py`, `pages/4_Admin.py` | 예찬 | 판독 입력, 관리자 화면 |
| `tests/` | 각자 | 자기 모듈 테스트 |

다른 사람 파일을 고쳐야 하면 직접 고치지 말고 Issue로 요청합니다.

새 화면을 추가하면 `app.py`의 `st.Page(...)`와 `MENU_BY_ROLE`에 등록해야 메뉴에 나타납니다(채민에게 요청).

## 로컬 실행

```bash
# 1. 가상환경 (Python 3.11 이상)
python -m venv .venv
# Windows: .venv\Scripts\activate   /  macOS·Linux: source .venv/bin/activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 설정 파일 만들기
#    .streamlit/secrets.example.toml 을 복사해 .streamlit/secrets.toml 로 저장
#    1주차는 auth_mode = "fake" 그대로 두면 Firebase 없이 실행됨

# 4. 실행
streamlit run app.py
```

## 테스트

```bash
pytest
```

## 비밀키와 데이터

- `.streamlit/secrets.toml`과 Firebase 서비스 계정 키는 **GitHub에 올리지 않습니다**(`.gitignore` 처리됨). 값은 팀 개인 메시지로 전달합니다.
- 영상 데이터는 라이선스상 재배포가 안 되므로 `data/`에 두고 올리지 않습니다.

| 용도 | 데이터셋 | 받는 곳 |
| --- | --- | --- |
| 메인 | SIIM-ACR Pneumothorax Segmentation | Kaggle (가입·대회 약관 동의 필요) |
| 불일치 시나리오 | VinBigData Chest X-ray Abnormalities | Kaggle (가입·대회 약관 동의 필요) |
| 개발 초반 테스트 | LIDC-IDRI DX 샘플 (CC BY 3.0) | TCIA |

TODO(채민): 데이터 받는 방법, 사용한 일부 데이터 목록, 출처·인용 정리

## 협업

- main 직접 push 금지. Issue → 브랜치 → PR → 리뷰 1명 승인 → 병합
- 브랜치: `feat/기능`, `fix/오류`, `exp/실험`, `docs/문서`
- 커밋: `[영역] 무엇을 + 왜`
- 리뷰 순서: 채민 → 주연, 주연 → 예찬, 예찬 → 채민

## 배포 (JCloud)

TODO(채민): JCloud 실행 방법, 외부 접속 주소, 재시작 방법
