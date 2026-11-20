"""写入演示账号与演示数据，可重复执行。

演示账号：
    学生   student@example.com / Student123!
    企业   company@example.com / Company123!
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.auth import register_company, register_student  # noqa: E402
from core.config import now_iso  # noqa: E402
from core.db import get_connection, init_db, query_one  # noqa: E402

STUDENT_EMAIL = "student@example.com"
STUDENT_PASSWORD = "Student123!"
COMPANY_EMAIL = "company@example.com"
COMPANY_PASSWORD = "Company123!"

DEMO_JOBS = [
    {
        "title": "Python 后端开发实习生",
        "job_type": "INTERN",
        "city": "上海",
        "salary": "200-300 元/天",
        "description": "参与内部平台后端接口开发与测试。",
        "requirements": "熟悉 Python 基础，了解 SQL，能阅读英文文档。",
    },
    {
        "title": "2027 届数据分析校招生",
        "job_type": "CAMPUS",
        "city": "杭州",
        "salary": "15-25K",
        "description": "负责业务数据分析、报表与指标体系建设。",
        "requirements": "统计或计算机相关专业，掌握 SQL 与 Python。",
    },
]


def _ensure_student() -> int:
    with get_connection() as conn:
        user = query_one(conn, "SELECT id FROM users WHERE email = ?", (STUDENT_EMAIL,))
    if user is None:
        user_id = register_student(STUDENT_EMAIL, STUDENT_PASSWORD, "演示学生")
    else:
        user_id = int(user["id"])

    with get_connection() as conn:
        resume = query_one(
            conn, "SELECT id FROM resumes WHERE student_id = ?", (user_id,)
        )
        if resume is None:
            conn.execute(
                """
                INSERT INTO resumes
                    (student_id, real_name, phone, school, major,
                     graduation_year, skills, summary, file_path, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'VERIFIED', ?)
                """,
                (
                    user_id,
                    "演示学生",
                    "13800000000",
                    "示例大学",
                    "计算机科学与技术",
                    2027,
                    "Python / SQL / Streamlit",
                    "热爱后端开发，参与过课程项目。",
                    now_iso(),
                ),
            )
    return user_id


def _ensure_company() -> int:
    with get_connection() as conn:
        user = query_one(conn, "SELECT id FROM users WHERE email = ?", (COMPANY_EMAIL,))
    if user is None:
        user_id = register_company(COMPANY_EMAIL, COMPANY_PASSWORD, "示例科技有限公司")
    else:
        user_id = int(user["id"])

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE companies
            SET name = ?, license_no = ?, hr_name = ?, hr_email = ?,
                status = 'APPROVED', hr_status = 'APPROVED', updated_at = ?
            WHERE user_id = ?
            """,
            (
                "示例科技有限公司",
                "91310000DEMO0001X",
                "王招聘",
                "hr@example.com",
                now_iso(),
                user_id,
            ),
        )
    return user_id


def _ensure_jobs(company_user_id: int) -> None:
    with get_connection() as conn:
        company = query_one(
            conn,
            "SELECT id FROM companies WHERE user_id = ?",
            (company_user_id,),
        )
        if company is None:
            return
        company_id = int(company["id"])

        for job in DEMO_JOBS:
            exists = query_one(
                conn,
                "SELECT id FROM jobs WHERE company_id = ? AND title = ?",
                (company_id, job["title"]),
            )
            if exists is not None:
                continue
            timestamp = now_iso()
            conn.execute(
                """
                INSERT INTO jobs
                    (company_id, title, job_type, city, salary, description,
                     requirements, status, is_featured, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED', 0, ?, ?)
                """,
                (
                    company_id,
                    job["title"],
                    job["job_type"],
                    job["city"],
                    job["salary"],
                    job["description"],
                    job["requirements"],
                    timestamp,
                    timestamp,
                ),
            )


def main() -> None:
    init_db()
    _ensure_student()
    company_user_id = _ensure_company()
    _ensure_jobs(company_user_id)
    print("演示数据已就绪：")
    print(f"  学生：{STUDENT_EMAIL} / {STUDENT_PASSWORD}")
    print(f"  企业：{COMPANY_EMAIL} / {COMPANY_PASSWORD}")


if __name__ == "__main__":
    main()
