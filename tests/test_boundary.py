"""边界条件测试：输入长度、取值区间、文件与字符串边界。"""

import pytest

from core import auth
from core.config import MAX_UPLOAD_BYTES
from core.errors import BusinessError
from core.security import validate_upload
from services import jobs, students
from tests.support import (
    job_payload,
    make_company,
    make_student,
    resume_payload,
)


def test_password_length_boundary(db_path):
    """TC-B01：密码 7 位拒绝，8 位通过。"""
    with pytest.raises(BusinessError) as exc_info:
        auth.register_student("short@example.com", "1234567", "短密码")
    assert exc_info.value.code == "VALIDATION_ERROR"

    user_id = auth.register_student("exact@example.com", "12345678", "刚好八位")
    assert auth.get_user(user_id) is not None


@pytest.mark.parametrize(
    "email",
    ["plain", "a@b", "a b@example.com", "@example.com", "a@@example.com"],
)
def test_invalid_email_formats(db_path, email):
    """TC-B02：明显非法的邮箱格式全部拒绝。"""
    with pytest.raises(BusinessError) as exc_info:
        auth.register_student(email, "Student123!", "张三")
    assert exc_info.value.code == "VALIDATION_ERROR"


def test_email_is_case_insensitive(db_path):
    """TC-B03：大小写不同的同一邮箱不能重复注册。"""
    auth.register_student("Case@Example.com", "Student123!", "张三")

    with pytest.raises(BusinessError) as exc_info:
        auth.register_student("case@example.com", "Student123!", "李四")

    assert exc_info.value.code == "EMAIL_EXISTS"


@pytest.mark.parametrize("year", [1999, 2101])
def test_graduation_year_out_of_range(db_path, year):
    """TC-B04：毕业年份超出 2000-2100 拒绝。"""
    student_id = make_student()

    with pytest.raises(BusinessError) as exc_info:
        students.save_resume(student_id, resume_payload(graduation_year=year))

    assert exc_info.value.code == "VALIDATION_ERROR"


@pytest.mark.parametrize("year", [2000, 2100])
def test_graduation_year_boundary_accepted(db_path, year):
    """TC-B05：毕业年份上下边界值可以保存。"""
    student_id = make_student()

    resume = students.save_resume(student_id, resume_payload(graduation_year=year))

    assert resume["graduation_year"] == year


def test_job_description_length_boundary(db_path):
    """TC-B06：职位描述 19 字拒绝，20 字通过。"""
    company_id = make_company()

    with pytest.raises(BusinessError) as exc_info:
        jobs.create_job(company_id, job_payload(description="短" * 19))
    assert exc_info.value.code == "VALIDATION_ERROR"

    job = jobs.create_job(company_id, job_payload(description="字" * 20))
    assert job["status"] == "PENDING"


def test_invalid_job_type_rejected(db_path):
    """TC-B07：非法职位类型拒绝。"""
    company_id = make_company()

    with pytest.raises(BusinessError) as exc_info:
        jobs.create_job(company_id, job_payload(job_type="FULLTIME"))

    assert exc_info.value.code == "VALIDATION_ERROR"


def test_upload_size_boundaries():
    """TC-B08：0 字节拒绝；正好 5 MB 通过；5 MB+1 拒绝。"""
    with pytest.raises(BusinessError) as exc_info:
        validate_upload("resume.pdf", 0)
    assert exc_info.value.code == "FILE_INVALID"

    assert validate_upload("resume.pdf", MAX_UPLOAD_BYTES) == ".pdf"

    with pytest.raises(BusinessError) as exc_info:
        validate_upload("resume.pdf", MAX_UPLOAD_BYTES + 1)
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_upload_extension_case_and_double_extension():
    """TC-B09：扩展名大小写不敏感；双扩展名按最后一个判断。"""
    assert validate_upload("我的简历.PDF", 100) == ".pdf"
    assert validate_upload("resume.DocX", 100) == ".docx"

    with pytest.raises(BusinessError) as exc_info:
        validate_upload("resume.pdf.exe", 100)
    assert exc_info.value.code == "FILE_INVALID"


def test_blank_resume_fields_rejected(db_path):
    """TC-B10：纯空格字段视为未填写。"""
    student_id = make_student()

    with pytest.raises(BusinessError) as exc_info:
        students.save_resume(student_id, resume_payload(real_name="   "))

    assert exc_info.value.code == "VALIDATION_ERROR"


def test_salary_is_optional(db_path):
    """TC-B11：薪资可以为空。"""
    company_id = make_company()

    job = jobs.create_job(company_id, job_payload(salary=""))

    assert job["salary"] is None


def test_long_text_is_stored_without_truncation(db_path):
    """TC-B12：2000 字简介可完整保存。"""
    student_id = make_student()
    summary = "长" * 2000

    resume = students.save_resume(student_id, resume_payload(summary=summary))

    assert resume["summary"] == summary


def test_sql_like_keyword_is_treated_as_data(db_path):
    """TC-B13：SQL 注入风格关键词不会报错或破坏查询。"""
    company_id = make_company()
    jobs.create_job(company_id, job_payload())

    results = jobs.search_jobs(keyword="%' OR 1=1 --")

    assert isinstance(results, list)
