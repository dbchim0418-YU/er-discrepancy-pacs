import pytest

from core.storage import StorageError, read_file, save_file, save_with_record


def test_save_and_read(tmp_path):
    path = save_file(b"abc", "originals/C-0001/img1.png", root=tmp_path)
    assert read_file(path, root=tmp_path) == b"abc"


def test_original_is_never_overwritten(tmp_path):
    save_file(b"first", "originals/C-0001/img1.png", root=tmp_path)
    with pytest.raises(FileExistsError):
        save_file(b"second", "originals/C-0001/img1.png", root=tmp_path)
    assert read_file("originals/C-0001/img1.png", root=tmp_path) == b"first"


def test_path_outside_root_is_rejected(tmp_path):
    with pytest.raises(StorageError):
        save_file(b"x", "../escape.png", root=tmp_path)


def test_file_is_removed_when_db_record_fails(tmp_path):
    def failing_record(saved_path):
        raise RuntimeError("Firestore 쓰기 실패")

    with pytest.raises(StorageError):
        save_with_record(b"data", "originals/C-0002/img.png", failing_record, root=tmp_path)
    # DB 기록이 실패하면 파일도 남지 않아야 한다
    assert not (tmp_path / "originals/C-0002/img.png").exists()


def test_record_result_is_returned(tmp_path):
    result = save_with_record(b"data", "originals/C-0003/img.png", lambda p: {"file_path": p}, root=tmp_path)
    assert result == {"file_path": "originals/C-0003/img.png"}
