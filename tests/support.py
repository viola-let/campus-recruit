"""扩展测试使用的数据工厂，避免每个测试重复建号与造数据。"""

from core import auth
from core.config import now_iso
from core.db import get_connection

STUDENT_PASSWORD = "Student123!"
COMPANY_PASSWORD = "Company123!"
ADMIN_PASSWORD = "ChangeMe123"


def resume_payload(**overrides):
    payload = {
        "real_name": "张三",
        "phone": "13800000000",
        "school": "示例大学",
        "major": "计算机科学与技术",
        "graduation_year": 2027,
        "skills": "Python / SQL",
        "summary": "热爱后端开发",
    }
    payload.update(overrides)
    return payload


def job_payload(**overrides):
    payload = {
        "title": "Python 后端工程师",
        "job_type": "CAMPUS",
        "city": "杭州",
        "salary": "20-30K",
        "description": "负责校招平台后端接口开发、测试与日常维护工作。",
        "requirements": "熟悉 Python 与 SQL",
    }
    payload.update(overrides)
    return payload


def make_student(email="student@example.com", name="张三") -> int:
    return auth.register_student(email, STUDENT_PASSWORD, name)


def make_company(email="company@example.com", name="示例科技", approved=True) -> int:
    user_id = auth.register_company(email, COMPANY_PASSWORD, name)
    if approved:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE companies
                SET license_no = '91310000TEST0001X', hr_name = '李招聘',
                    hr_email = 'hr@example.com', status = 'APPROVED',
                    hr_status = 'APPROVED', updated_at = ?
                WHERE user_id = ?
                """,
                (now_iso(), user_id),
            )
    return user_id


def make_admin(email="admin@example.com") -> int:
    return auth.create_admin(email, ADMIN_PASSWORD, "平台管理员")


def make_job(
    company_user_id: int,
    status="APPROVED",
    title="Python 后端实习生",
    job_type="INTERN",
    city="上海",
) -> int:
    with get_connection() as conn:
        company = conn.execute(
            "SELECT id FROM companies WHERE user_id = ?", (company_user_id,)
        ).fetchone()
        timestamp = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO jobs
                (company_id, title, job_type, city, salary, description,
                 requirements, status, is_featured, created_at, updated_at)
            VALUES (?, ?, ?, ?, '200 元/天', ?, ?, ?, 0, ?, ?)
            """,
            (
                company["id"],
                title,
                job_type,
                city,
                "参与内部平台后端接口开发与测试，学习业务流程。",
                "熟悉 Python 基础，了解 SQL。",
                status,
                timestamp,
                timestamp,
            ),
        )
        return int(cursor.lastrowid)


def set_resume_status(student_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE resumes SET status = ?, updated_at = ? WHERE student_id = ?",
            (status, now_iso(), student_id),
        )
