"""SQLite 连接与建表。

约定：
- 每次操作打开一个短连接，用完立即关闭，不使用模块级全局连接；
- 连接开启外键约束；
- 查询结果统一转换为普通 dict，方便页面与服务层使用。
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from core.config import get_db_path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('student', 'company', 'admin')),
    display_name  TEXT    NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    license_no    TEXT    NOT NULL,
    license_file  TEXT,
    hr_name       TEXT    NOT NULL,
    hr_email      TEXT    NOT NULL,
    hr_proof_file TEXT,
    logo_path     TEXT,
    intro         TEXT,
    culture       TEXT,
    industry      TEXT,
    company_size  TEXT,
    funding_stage TEXT,
    city          TEXT,
    benefits      TEXT,
    status        TEXT    NOT NULL DEFAULT 'PENDING'
                  CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    hr_status     TEXT    NOT NULL DEFAULT 'PENDING'
                  CHECK (hr_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title        TEXT    NOT NULL,
    job_type     TEXT    NOT NULL CHECK (job_type IN ('CAMPUS', 'INTERN')),
    city         TEXT    NOT NULL,
    salary       TEXT,
    description  TEXT    NOT NULL,
    requirements TEXT,
    status       TEXT    NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CLOSED')),
    is_featured  INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    real_name       TEXT    NOT NULL,
    phone           TEXT    NOT NULL,
    school          TEXT    NOT NULL,
    major           TEXT    NOT NULL,
    graduation_year INTEGER NOT NULL,
    skills          TEXT,
    summary         TEXT,
    file_path       TEXT,
    status          TEXT    NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'VERIFIED', 'REJECTED')),
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id               INTEGER NOT NULL REFERENCES jobs(id),
    student_id           INTEGER NOT NULL REFERENCES users(id),
    resume_id            INTEGER NOT NULL REFERENCES resumes(id),
    resume_snapshot      TEXT    NOT NULL,
    resume_file_snapshot TEXT,
    status               TEXT    NOT NULL DEFAULT 'SUBMITTED'
                         CHECK (status IN ('SUBMITTED', 'VIEWED', 'SHORTLISTED',
                                           'REJECTED', 'HIRED')),
    feedback             TEXT,
    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL,
    UNIQUE (job_id, student_id)
);

CREATE TABLE IF NOT EXISTS review_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT    NOT NULL
                CHECK (entity_type IN ('company_license', 'company_hr',
                                       'job', 'resume')),
    entity_id   INTEGER NOT NULL,
    decision    TEXT    NOT NULL
                CHECK (decision IN ('APPROVED', 'REJECTED', 'VERIFIED')),
    note        TEXT,
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id     INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    UNIQUE (student_id, job_id)
);

CREATE TABLE IF NOT EXISTS culture_posts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    employment_status TEXT    NOT NULL
                      CHECK (employment_status IN
                             ('CURRENT', 'FORMER', 'INTERN', 'NONE')),
    is_verified       INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1)),
    is_anonymous      INTEGER NOT NULL DEFAULT 1 CHECK (is_anonymous IN (0, 1)),
    topic             TEXT    NOT NULL CHECK (topic IN ('experience', 'question')),
    title             TEXT    NOT NULL,
    content           TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    official_reply    TEXT,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS company_reviews (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id        INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    employment_status TEXT    NOT NULL
                      CHECK (employment_status IN ('CURRENT', 'FORMER', 'INTERN')),
    growth            INTEGER NOT NULL CHECK (growth BETWEEN 1 AND 5),
    salary            INTEGER NOT NULL CHECK (salary BETWEEN 1 AND 5),
    intensity         INTEGER NOT NULL CHECK (intensity BETWEEN 1 AND 5),
    interview         INTEGER NOT NULL CHECK (interview BETWEEN 1 AND 5),
    recommend         INTEGER NOT NULL CHECK (recommend BETWEEN 1 AND 5),
    content           TEXT    NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL,
    UNIQUE (user_id, company_id, employment_status)
);

CREATE TABLE IF NOT EXISTS micro_tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    city        TEXT    NOT NULL,
    reward      TEXT,
    schedule    TEXT,
    headcount   INTEGER NOT NULL DEFAULT 1 CHECK (headcount BETWEEN 1 AND 100),
    status      TEXT    NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CLOSED')),
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS task_signups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL REFERENCES micro_tasks(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    UNIQUE (task_id, student_id)
);

CREATE TABLE IF NOT EXISTS job_views (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    UNIQUE (job_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_status        ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_company       ON jobs (company_id);
CREATE INDEX IF NOT EXISTS idx_applications_job   ON applications (job_id);
CREATE INDEX IF NOT EXISTS idx_applications_stu   ON applications (student_id);
CREATE INDEX IF NOT EXISTS idx_review_entity      ON review_logs
    (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_favorites_student  ON favorites (student_id);
CREATE INDEX IF NOT EXISTS idx_culture_company    ON culture_posts (company_id);
CREATE INDEX IF NOT EXISTS idx_culture_status     ON culture_posts (status);
CREATE INDEX IF NOT EXISTS idx_reviews_company    ON company_reviews (company_id);
CREATE INDEX IF NOT EXISTS idx_reviews_status     ON company_reviews (status);
CREATE INDEX IF NOT EXISTS idx_tasks_company      ON micro_tasks (company_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status       ON micro_tasks (status);
CREATE INDEX IF NOT EXISTS idx_task_signups_task  ON task_signups (task_id);
CREATE INDEX IF NOT EXISTS idx_job_views_job      ON job_views (job_id);
"""

# 老库升级：companies 表新增的品牌展示字段
COMPANY_BRANDING_COLUMNS = {
    "logo_path": "TEXT",
    "intro": "TEXT",
    "culture": "TEXT",
    "industry": "TEXT",
    "company_size": "TEXT",
    "funding_stage": "TEXT",
    "city": "TEXT",
    "benefits": "TEXT",
}

# 老库升级：jobs 表新增的急招字段
JOB_EXTRA_COLUMNS = {
    "is_urgent": "INTEGER NOT NULL DEFAULT 0",
    "urgent_until": "TEXT",
}


def _migrate(conn: sqlite3.Connection) -> None:
    """为已存在的数据库补充新增列，可重复执行。"""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info('companies')")}
    for name, ddl in COMPANY_BRANDING_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {name} {ddl}")

    existing_jobs = {row["name"] for row in conn.execute("PRAGMA table_info('jobs')")}
    for name, ddl in JOB_EXTRA_COLUMNS.items():
        if name not in existing_jobs:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}")


@contextmanager
def get_connection(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """打开一个短连接，正常结束自动提交，异常自动回滚。"""
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> None:
    """创建全部表与索引，并为老库补充新增字段；可重复执行。"""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate(conn)


def query_one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    """查询单行，返回 dict 或 None。"""
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row is not None else None


def query_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    """查询多行，返回 dict 列表。"""
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
