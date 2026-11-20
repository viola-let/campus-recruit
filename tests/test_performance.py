"""性能压力测试：1000 条职位数据下的检索、统计与投递耗时。"""

import time

from core.config import now_iso
from core.db import get_connection
from services import admin, applications, jobs, students
from tests.support import (
    make_admin,
    make_company,
    make_student,
    resume_payload,
)

JOB_COUNT = 1000
CITIES = ["杭州", "上海", "北京"]
DESCRIPTION = "负责校招平台后端接口开发、测试与日常维护工作。"


def _seed_jobs(company_user_id: int, count: int = JOB_COUNT) -> None:
    with get_connection() as conn:
        company_id = conn.execute(
            "SELECT id FROM companies WHERE user_id = ?", (company_user_id,)
        ).fetchone()[0]
        timestamp = now_iso()
        rows = [
            (
                company_id,
                f"压力测试职位 {index}",
                "CAMPUS" if index % 2 == 0 else "INTERN",
                CITIES[index % len(CITIES)],
                "20-30K",
                DESCRIPTION,
                "熟悉 Python 与 SQL",
                "APPROVED",
                timestamp,
                timestamp,
            )
            for index in range(count)
        ]
        conn.executemany(
            """
            INSERT INTO jobs
                (company_id, title, job_type, city, salary, description,
                 requirements, status, is_featured, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            rows,
        )


def _verify_student(student_id: int) -> None:
    students.save_resume(student_id, resume_payload())
    resume_id = students.get_resume(student_id)["id"]
    students.review_resume(make_admin(), resume_id, "VERIFIED")


def test_search_with_filters_under_one_second(db_path):
    """TC-P01：1000 条职位下，关键词+城市+类型筛选 < 1 秒。"""
    company_id = make_company()
    _seed_jobs(company_id)

    started = time.perf_counter()
    results = jobs.search_jobs(keyword="压力测试", city="杭州", job_type="CAMPUS")
    elapsed = time.perf_counter() - started
    print(f"\nPERF TC-P01 search_filters={elapsed:.3f}s results={len(results)}")

    assert results
    assert elapsed < 1.0


def test_search_without_filters_under_one_second(db_path):
    """TC-P02：1000 条职位下，无条件列表（推荐+时间排序）< 1 秒。"""
    company_id = make_company()
    _seed_jobs(company_id)

    started = time.perf_counter()
    results = jobs.search_jobs(limit=200)
    elapsed = time.perf_counter() - started
    print(f"\nPERF TC-P02 search_all={elapsed:.3f}s results={len(results)}")

    assert len(results) == 200
    assert elapsed < 1.0


def test_dashboard_counts_under_one_second(db_path):
    """TC-P03：1000 条职位下，管理端 6 项统计 < 1 秒。"""
    admin_id = make_admin()
    company_id = make_company()
    _seed_jobs(company_id)

    started = time.perf_counter()
    counts = admin.dashboard_counts(admin_id)
    elapsed = time.perf_counter() - started
    print(f"\nPERF TC-P03 dashboard={elapsed:.3f}s")

    assert counts["pending_jobs"] == 0
    assert elapsed < 1.0


def test_apply_under_one_second_with_many_jobs(db_path):
    """TC-P04：1000 条职位下，投递耗时 < 1 秒。"""
    company_id = make_company()
    _seed_jobs(company_id)
    student_id = make_student()
    _verify_student(student_id)
    job_id = jobs.search_jobs(limit=1)[0]["id"]

    started = time.perf_counter()
    application = applications.apply_to_job(student_id, job_id)
    elapsed = time.perf_counter() - started
    print(f"\nPERF TC-P04 apply={elapsed:.3f}s")

    assert application["status"] == "SUBMITTED"
    assert elapsed < 1.0


def test_candidate_query_under_one_second(db_path):
    """TC-P05：1000 条职位下，企业候选人查询 < 1 秒。"""
    company_id = make_company()
    _seed_jobs(company_id)
    student_id = make_student()
    _verify_student(student_id)
    job_id = jobs.search_jobs(limit=1)[0]["id"]
    applications.apply_to_job(student_id, job_id)

    started = time.perf_counter()
    candidates = applications.list_job_candidates(company_id)
    elapsed = time.perf_counter() - started
    print(f"\nPERF TC-P05 candidates={elapsed:.3f}s rows={len(candidates)}")

    assert len(candidates) == 1
    assert elapsed < 1.0
