"""种子数据测试：数据规模、关联关系、状态覆盖与安全重置。"""

import json
import re

from core import auth
from core.db import get_connection
from scripts import seed_test_data

SEED_DOMAIN = seed_test_data.SEED_DOMAIN


def _count(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def test_seed_volume_and_diversity(db_path):
    """TC-D01：至少 20 家公司、50 份简历、30 个岗位，且覆盖多行业与多类型。"""
    summary = seed_test_data.seed()

    assert summary["companies"] >= 20
    assert summary["resumes"] >= 50
    assert summary["jobs"] >= 30
    assert summary["applications"] >= 90

    with get_connection() as conn:
        company_names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM companies WHERE name LIKE '%（%'"
            ).fetchall()
        ]
        summaries = [
            row[0]
            for row in conn.execute(
                "SELECT summary FROM resumes WHERE summary IS NOT NULL"
            ).fetchall()
        ]
        titles = [row[0] for row in conn.execute("SELECT title FROM jobs").fetchall()]

    industries = set()
    cities = set()
    for name in company_names:
        match = re.search(r"（([^）]+)）", name)
        assert match is not None
        parts = match.group(1).split("·")
        assert len(parts) == 4
        industries.add(parts[0])
        cities.add(parts[3])

    assert len(industries) >= 10
    assert len(cities) >= 8
    assert {"互联网", "金融", "制造业", "消费品"} <= industries

    for level in ("应届生", "初级工程师", "中级工程师", "高级工程师", "技术管理"):
        assert any(f"【层级】{level}" in text for text in summaries)

    categories = {"技术", "产品", "运营", "市场", "职能"}
    for category in categories:
        assert sum(1 for title in titles if title.startswith(f"【{category}】")) >= 4


def test_seed_status_coverage(db_path):
    """TC-D02：简历、职位、投递覆盖所有业务状态。"""
    seed_test_data.seed()

    with get_connection() as conn:
        resume_status = {
            row[0]
            for row in conn.execute("SELECT DISTINCT status FROM resumes").fetchall()
        }
        job_status = {
            row[0]
            for row in conn.execute("SELECT DISTINCT status FROM jobs").fetchall()
        }
        application_status = {
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT status FROM applications"
            ).fetchall()
        }
        featured = _count(conn, "SELECT COUNT(*) FROM jobs WHERE is_featured = 1")

    assert {"PENDING", "VERIFIED", "REJECTED"} <= resume_status
    assert {"APPROVED", "PENDING", "REJECTED", "CLOSED"} <= job_status
    assert {"SUBMITTED", "VIEWED", "SHORTLISTED", "HIRED", "REJECTED"} <= (
        application_status
    )
    assert featured >= 5


def test_seed_relationships_are_consistent(db_path):
    """TC-D03：职位归属、投递关联、快照与审核记录逻辑一致。"""
    seed_test_data.seed()

    with get_connection() as conn:
        invalid_company_jobs = _count(
            conn,
            """
            SELECT COUNT(*) FROM jobs j
            JOIN companies c ON c.id = j.company_id
            WHERE c.status != 'APPROVED' OR c.hr_status != 'APPROVED'
            """,
        )
        broken_applications = _count(
            conn,
            """
            SELECT COUNT(*) FROM applications a
            LEFT JOIN jobs j ON j.id = a.job_id
            LEFT JOIN resumes r ON r.id = a.resume_id
            LEFT JOIN users u ON u.id = a.student_id
            WHERE j.id IS NULL OR r.id IS NULL OR u.id IS NULL
            """,
        )
        duplicate_applications = _count(
            conn,
            """
            SELECT COUNT(*) FROM (
                SELECT job_id, student_id FROM applications
                GROUP BY job_id, student_id HAVING COUNT(*) > 1
            )
            """,
        )
        non_approved_job_applications = _count(
            conn,
            """
            SELECT COUNT(*) FROM applications a
            JOIN jobs j ON j.id = a.job_id
            WHERE j.status != 'APPROVED'
            """,
        )
        underfilled_jobs = _count(
            conn,
            """
            SELECT COUNT(*) FROM jobs j
            WHERE j.status = 'APPROVED'
              AND (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) < 3
            """,
        )
        snapshots = [
            row[0]
            for row in conn.execute(
                "SELECT resume_snapshot FROM applications LIMIT 10"
            ).fetchall()
        ]
        non_seed_users = _count(
            conn,
            "SELECT COUNT(*) FROM users WHERE email NOT LIKE ?",
            (f"%{SEED_DOMAIN}",),
        )

    assert invalid_company_jobs == 0
    assert broken_applications == 0
    assert duplicate_applications == 0
    assert non_approved_job_applications == 0
    assert underfilled_jobs == 0
    assert non_seed_users >= 1

    for raw in snapshots:
        snapshot = json.loads(raw)
        assert snapshot["school"]
        assert "期望薪资" in snapshot["summary"]


def test_seed_is_idempotent_and_preserves_real_data(db_path):
    """TC-D04：重复导入数量稳定，且不删除真实账号。"""
    real_student = auth.register_student(
        "real_student@example.com", "Student123!", "真实学生"
    )
    real_company = auth.register_company(
        "real_company@example.com", "Company123!", "真实公司"
    )

    first = seed_test_data.seed()
    second = seed_test_data.seed()

    assert first == second

    with get_connection() as conn:
        assert (
            _count(conn, "SELECT COUNT(*) FROM users WHERE id = ?", (real_student,))
            == 1
        )
        assert (
            _count(conn, "SELECT COUNT(*) FROM users WHERE id = ?", (real_company,))
            == 1
        )
        assert (
            _count(
                conn,
                "SELECT COUNT(*) FROM companies WHERE user_id = ?",
                (real_company,),
            )
            == 1
        )
        assert (
            _count(
                conn,
                "SELECT COUNT(*) FROM users WHERE email LIKE ?",
                (f"%{SEED_DOMAIN}",),
            )
            == 70
        )
