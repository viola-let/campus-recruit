"""项目配置：路径、枚举、业务常量、会话 Key。

原则：所有“魔法字符串”集中在这里，页面与服务层只引用常量。
"""

import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

# ============================================================
# 路径
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"

UPLOADS_DIR = BASE_DIR / "uploads"
RESUME_UPLOAD_DIR = UPLOADS_DIR / "resumes"
LICENSE_UPLOAD_DIR = UPLOADS_DIR / "licenses"
LOGO_UPLOAD_DIR = UPLOADS_DIR / "logos"


def get_db_path() -> Path:
    """返回当前使用的数据库路径。

    优先读取环境变量 CAMPUS_DB_PATH，便于测试使用临时数据库；
    未设置时使用 data/app.db。
    """
    override = os.environ.get("CAMPUS_DB_PATH")
    if override:
        return Path(override).expanduser()
    return DB_PATH


# ============================================================
# 业务常量
# ============================================================
MAX_UPLOAD_MB = 5
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx"}

MAX_LOGO_MB = 2
MAX_LOGO_BYTES = MAX_LOGO_MB * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

JOB_CATEGORIES = ["技术", "产品", "运营", "市场", "职能"]
PASSWORD_MIN_LENGTH = 8
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 200

# ---- v1.2 急招 / 社区口碑 / 小任务 ----
URGENT_MAX_DAYS = 30
URGENT_MAX_RATIO = 0.3
REVIEW_MIN_SAMPLE = 3
REVIEW_MIN_CONTENT = 50
POST_MIN_CONTENT = 30
QUESTION_MIN_CONTENT = 10
POST_DAILY_LIMIT = 3
EXPERIENCE_POST_INTERVAL_DAYS = 7

CONTENT_BLOCKLIST = (
    "刷单",
    "押金",
    "垫付",
    "返利",
    "拉人头",
    "下载app",
    "日结高薪",
    "内部渠道",
    "包过",
)

# 统一时区：中国标准时间，无夏令时，固定 UTC+8
CN_TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    """返回 Asia/Shanghai 时区的 ISO 8601 字符串（精确到秒）。"""
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


# ============================================================
# 会话状态 Key
# ============================================================
SESSION_AUTH_USER = "auth_user"
SESSION_FLASH = "flash"


# ============================================================
# 枚举
# ============================================================
class Role(str, Enum):
    """用户角色，取值与数据库 CHECK 约束一致。"""

    STUDENT = "student"
    COMPANY = "company"
    ADMIN = "admin"


class ReviewStatus(str, Enum):
    """企业资质 / HR / 职位的审核状态。"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ResumeStatus(str, Enum):
    """简历核查状态。"""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class JobStatus(str, Enum):
    """职位状态。"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class JobType(str, Enum):
    """职位类型。"""

    CAMPUS = "CAMPUS"
    INTERN = "INTERN"


class ApplicationStatus(str, Enum):
    """投递状态。"""

    SUBMITTED = "SUBMITTED"
    VIEWED = "VIEWED"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    HIRED = "HIRED"


ROLE_LABELS = {
    Role.STUDENT.value: "学生",
    Role.COMPANY.value: "企业",
    Role.ADMIN.value: "平台管理员",
}

JOB_TYPE_LABELS = {
    JobType.CAMPUS.value: "校招",
    JobType.INTERN.value: "实习",
}

REVIEW_STATUS_LABELS = {
    ReviewStatus.PENDING.value: "待审核",
    ReviewStatus.APPROVED.value: "已通过",
    ReviewStatus.REJECTED.value: "已拒绝",
}

RESUME_STATUS_LABELS = {
    ResumeStatus.PENDING.value: "待核查",
    ResumeStatus.VERIFIED.value: "已核查",
    ResumeStatus.REJECTED.value: "已拒绝",
}

JOB_STATUS_LABELS = {
    JobStatus.PENDING.value: "待审核",
    JobStatus.APPROVED.value: "已通过",
    JobStatus.REJECTED.value: "已拒绝",
    JobStatus.CLOSED.value: "已关闭",
}

APPLICATION_STATUS_LABELS = {
    ApplicationStatus.SUBMITTED.value: "已投递",
    ApplicationStatus.VIEWED.value: "已查看",
    ApplicationStatus.SHORTLISTED.value: "进入面试",
    ApplicationStatus.REJECTED.value: "不合适",
    ApplicationStatus.HIRED.value: "已录用",
}


class EmploymentStatus(str, Enum):
    """校园社区发言者的企业任职状态。"""

    CURRENT = "CURRENT"
    FORMER = "FORMER"
    INTERN = "INTERN"
    NONE = "NONE"


class ContentStatus(str, Enum):
    """UGC 内容审核状态。"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MicroTaskStatus(str, Enum):
    """小任务状态。"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


EMPLOYMENT_STATUS_LABELS = {
    EmploymentStatus.CURRENT.value: "在职",
    EmploymentStatus.FORMER.value: "曾任职",
    EmploymentStatus.INTERN.value: "实习过",
    EmploymentStatus.NONE.value: "未任职",
}

CONTENT_STATUS_LABELS = {
    ContentStatus.PENDING.value: "待审核",
    ContentStatus.APPROVED.value: "已通过",
    ContentStatus.REJECTED.value: "已拒绝",
}

MICRO_TASK_STATUS_LABELS = {
    MicroTaskStatus.PENDING.value: "待审核",
    MicroTaskStatus.APPROVED.value: "招募中",
    MicroTaskStatus.REJECTED.value: "已拒绝",
    MicroTaskStatus.CLOSED.value: "已结束",
}

REVIEW_DIMENSION_LABELS = {
    "growth": "成长空间",
    "salary": "薪酬福利",
    "intensity": "工作强度",
    "interview": "面试体验",
    "recommend": "推荐意愿",
}
