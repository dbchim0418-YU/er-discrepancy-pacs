"""예비·최종 판독 저장. 주인: 예찬

Firestore readings 컬렉션 필드(개발 규칙 5번):
reading_id, case_id, kind(prelim/final), finding, side, size, memo, author_uid, created_at, revisions
권한: 예비 소견은 er, 최종 판독은 radiologist (core.auth.require_role 사용)
"""
# TODO(예찬): save_prelim(), save_final(), update_final()(수정 이력 포함)
