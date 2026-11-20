"""安全相关工具：密码哈希、上传校验、路径校验。

密码存储格式：
    pbkdf2_sha256$<迭代次数>$<Base64 盐>$<Base64 哈希>
"""

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from core.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_UPLOAD_EXTENSIONS,
    BASE_DIR,
    MAX_LOGO_BYTES,
    MAX_LOGO_MB,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    UPLOADS_DIR,
)
from core.errors import BusinessError

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
SALT_BYTES = 16

# REST 接口认证配置
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8
DEFAULT_JWT_SECRET = "campus-recruit-local-dev-secret-change-me"


def hash_password(password: str) -> str:
    """生成加盐哈希字符串，用于写入 users.password_hash。"""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, stored: str) -> bool:
    """校验明文密码与数据库中的哈希是否匹配。"""
    try:
        algorithm, iterations, salt_b64, digest_b64 = stored.split("$")
        if algorithm != PASSWORD_ALGORITHM:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _validate_file(
    filename: str,
    size: int,
    extensions: set[str],
    error_message: str,
    max_bytes: int,
    max_mb: int,
) -> str:
    """通用文件校验：扩展名、空文件与大小上限。"""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in extensions:
        raise BusinessError("FILE_INVALID", error_message)
    if size <= 0:
        raise BusinessError("FILE_INVALID", "文件内容为空")
    if size > max_bytes:
        raise BusinessError("FILE_TOO_LARGE", f"文件不能超过 {max_mb} MB")
    return suffix


def validate_upload(filename: str, size: int) -> str:
    """校验简历/证明材料，返回小写扩展名；不合法时抛 BusinessError。"""
    return _validate_file(
        filename,
        size,
        ALLOWED_UPLOAD_EXTENSIONS,
        "仅支持 PDF / DOCX 文件",
        MAX_UPLOAD_BYTES,
        MAX_UPLOAD_MB,
    )


def validate_image_upload(filename: str, size: int) -> str:
    """校验企业 logo 图片，返回小写扩展名。"""
    return _validate_file(
        filename,
        size,
        ALLOWED_IMAGE_EXTENSIONS,
        "仅支持 PNG / JPG / JPEG / WEBP 图片",
        MAX_LOGO_BYTES,
        MAX_LOGO_MB,
    )


def save_upload(filename: str, content: bytes, target_dir: Path) -> str:
    """保存上传文件，返回相对项目根目录的路径。

    文件名使用 UUID，避免原文件名造成的路径穿越与重名覆盖。
    """
    suffix = validate_upload(filename, len(content))
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid.uuid4().hex}{suffix}"
    target_path.write_bytes(content)
    return target_path.resolve().relative_to(BASE_DIR.resolve()).as_posix()


def save_image_upload(filename: str, content: bytes, target_dir: Path) -> str:
    """保存企业 logo 图片，返回相对项目根目录的路径。"""
    suffix = validate_image_upload(filename, len(content))
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid.uuid4().hex}{suffix}"
    target_path.write_bytes(content)
    return target_path.resolve().relative_to(BASE_DIR.resolve()).as_posix()


def resolve_upload_path(relative_path: str) -> Path:
    """把数据库中的相对路径还原为绝对路径，并确认它位于 uploads/ 内。"""
    candidate = (BASE_DIR / relative_path).resolve()
    uploads_root = UPLOADS_DIR.resolve()
    if uploads_root not in candidate.parents:
        raise BusinessError("NOT_FOUND", "文件不存在")
    return candidate


def get_jwt_secret() -> str:
    """读取 API_JWT_SECRET；本地开发未设置时使用固定默认值。"""
    return os.environ.get("API_JWT_SECRET") or DEFAULT_JWT_SECRET


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    """签发 JWT，返回 (token, 有效期秒数)。"""
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return token, JWT_EXPIRE_HOURS * 3600


def decode_access_token(token: str) -> dict:
    """校验并解析 JWT；无效或过期时抛出 jwt.PyJWTError。"""
    return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
