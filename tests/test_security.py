"""安全工具测试：密码哈希、上传校验与路径校验。"""

from pathlib import Path

import pytest

from core.config import MAX_UPLOAD_BYTES
from core.errors import BusinessError
from core.security import (
    hash_password,
    resolve_upload_path,
    save_upload,
    validate_upload,
    verify_password,
)


def test_hash_and_verify_password():
    stored = hash_password("Secret123!")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("Secret123!", stored) is True


def test_verify_wrong_password():
    stored = hash_password("Secret123!")
    assert verify_password("Wrong123!", stored) is False


def test_hash_does_not_contain_plaintext():
    stored = hash_password("Secret123!")
    assert "Secret123!" not in stored


def test_validate_upload_rejects_invalid_extension():
    with pytest.raises(BusinessError) as exc_info:
        validate_upload("virus.exe", 100)
    assert exc_info.value.code == "FILE_INVALID"


def test_validate_upload_rejects_large_file():
    with pytest.raises(BusinessError) as exc_info:
        validate_upload("resume.pdf", MAX_UPLOAD_BYTES + 1)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_save_upload_uses_uuid_filename(tmp_path, monkeypatch):
    monkeypatch.setattr("core.security.BASE_DIR", tmp_path)
    target_dir = tmp_path / "resumes"

    relative = save_upload("我的简历.PDF", b"pdf-content", target_dir)

    assert relative.startswith("resumes/")
    assert relative.endswith(".pdf")
    assert (tmp_path / relative).is_file()


def test_resolve_upload_path_blocks_traversal():
    with pytest.raises(BusinessError) as exc_info:
        resolve_upload_path("../../evil.txt")
    assert exc_info.value.code == "NOT_FOUND"


def test_resolve_upload_path_accepts_normal_file():
    path = resolve_upload_path("uploads/resumes/demo.pdf")
    assert Path(path).name == "demo.pdf"
