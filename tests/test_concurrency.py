"""并发场景测试：重复投递、重复注册、并发审核与状态竞争。"""

import threading

import pytest

from core import auth
from core.errors import BusinessError
from services import applications, jobs, students
from tests.support import (
    STUDENT_PASSWORD,
    job_payload,
    make_admin,
    make_company,
    make_job,
    make_student,
    resume_payload,
)


def _run_concurrently(worker, count=8):
    """用栅栏让线程尽量同时开始，返回每个线程的结果或异常。"""
    barrier = threading.Barrier(count)
    results = []
    lock = threading.Lock()

    def wrapped():
        barrier.wait()
        try:
            value = worker()
        except Exception as exc:  # noqa: BLE001 - 测试需要收集所有异常
            with lock:
                results.append(exc)
        else:
            with lock:
                results.append(value)

    threads = [threading.Thread(target=wrapped) for _ in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    return results


def _verified_student(email="student@example.com") -> int:
    student_id = make_student(email)
    students.save_resume(student_id, resume_payload())
    resume_id = students.get_resume(student_id)["id"]
    students.review_resume(make_admin(f"admin_{email}"), resume_id, "VERIFIED")
    return student_id


def test_concurrent_duplicate_applications(db_path):
    """TC-C01：8 个并发投递只能成功 1 次，不能出现数据库锁错误。"""
    student_id = _verified_student()
    company_id = make_company()
    job_id = make_job(company_id)

    def worker():
        try:
            applications.apply_to_job(student_id, job_id)
            return "ok"
        except BusinessError as exc:
            return exc.code

    results = _run_concurrently(worker)

    assert results.count("ok") == 1
    assert results.count("DUPLICATE_APPLICATION") == 7
    assert len(applications.list_my_applications(student_id)) == 1


def test_concurrent_same_email_registration(db_path):
    """TC-C02：同一邮箱并发注册只能成功 1 次。"""

    def worker():
        try:
            auth.register_student("race@example.com", STUDENT_PASSWORD, "并发用户")
            return "ok"
        except BusinessError as exc:
            return exc.code

    results = _run_concurrently(worker)

    assert results.count("ok") == 1
    assert results.count("EMAIL_EXISTS") == 7


def test_concurrent_admin_review_same_job(db_path):
    """TC-C03：多个管理员并发审核同一职位，只能有一个审核生效。"""
    company_id = make_company()
    job_id = make_job(company_id, status="PENDING")
    admin_ids = [make_admin(f"admin{i}@example.com") for i in range(6)]

    def worker(admin_id):
        try:
            jobs.review_job(admin_id, job_id, "APPROVED")
            return "ok"
        except BusinessError as exc:
            return exc.code

    barrier = threading.Barrier(len(admin_ids))
    results = []

    def run(admin_id):
        barrier.wait()
        results.append(worker(admin_id))

    threads = [threading.Thread(target=run, args=(admin_id,)) for admin_id in admin_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert results.count("ok") == 1
    assert results.count("INVALID_STATE") == len(admin_ids) - 1


def test_concurrent_status_transition_competition(db_path):
    """TC-C04：同一投递被并发改为“进入面试”和“不合适”，只能一个成功。"""
    student_id = _verified_student()
    company_id = make_company()
    job_id = make_job(company_id)
    application = applications.apply_to_job(student_id, job_id)
    applications.update_status(company_id, application["id"], "VIEWED")

    barrier = threading.Barrier(2)
    results = []

    def worker(new_status, feedback):
        barrier.wait()
        try:
            applications.update_status(
                company_id, application["id"], new_status, feedback
            )
            results.append("ok")
        except BusinessError as exc:
            results.append(exc.code)

    threads = [
        threading.Thread(target=worker, args=("SHORTLISTED", "进入面试")),
        threading.Thread(target=worker, args=("REJECTED", "不合适")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert results.count("ok") == 1


def test_concurrent_job_creation(db_path):
    """TC-C05：同一企业并发创建 8 个职位应全部成功。"""
    company_id = make_company()

    results = _run_concurrently(
        lambda: jobs.create_job(company_id, job_payload())["id"]
    )

    assert all(isinstance(item, int) for item in results), results
    assert len(jobs.list_company_jobs(company_id)) == 8


@pytest.mark.parametrize("attempt", [1, 2])
def test_repeated_seed_like_writes_are_stable(db_path, attempt):
    """TC-C06：重复的注册/写入操作不会破坏数据库。"""
    company_id = make_company(f"company{attempt}@example.com")
    jobs.create_job(company_id, job_payload())

    assert len(jobs.list_company_jobs(company_id)) == 1
