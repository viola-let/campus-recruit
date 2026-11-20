"""AppTest 页面冒烟测试（T-11、T-12）。"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import auth

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_anonymous_user_sees_login_form(db_path):
    """T-11：未登录时进入登录页，页面包含登录表单。"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert not at.exception
    labels = [item.label for item in at.text_input]
    assert "邮箱" in labels
    assert "密码" in labels


def test_student_login_shows_student_home(db_path):
    """T-12：学生登录后进入学生首页，页面无异常。"""
    user_id = auth.register_student(
        "smoke_student@example.com", "Student123!", "冒烟学生"
    )
    user = auth.get_user(user_id)

    at = AppTest.from_file(APP_PATH)
    at.session_state["auth_user"] = user
    at.run()

    assert not at.exception
    assert any("你好，冒烟学生" in item.value for item in at.html)


def _logged_in_app(user: dict) -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.session_state["auth_user"] = user
    return at.run()


def test_company_pages_render(db_path):
    user_id = auth.register_company(
        "smoke_company@example.com", "Company123!", "冒烟公司"
    )
    at = _logged_in_app(auth.get_user(user_id))

    for page in (
        "views/company/home.py",
        "views/company/profile.py",
        "views/company/jobs.py",
        "views/company/candidates.py",
    ):
        at.switch_page(page).run()
        assert not at.exception, page


def test_admin_pages_render(db_path):
    user_id = auth.create_admin("smoke_admin@example.com", "ChangeMe123")
    at = _logged_in_app(auth.get_user(user_id))

    for page in (
        "views/admin/home.py",
        "views/admin/companies.py",
        "views/admin/jobs.py",
        "views/admin/resumes.py",
    ):
        at.switch_page(page).run()
        assert not at.exception, page


def test_logout_clears_session(db_path):
    user_id = auth.register_student(
        "logout_student@example.com", "Student123!", "退出学生"
    )
    at = _logged_in_app(auth.get_user(user_id))

    at.sidebar.button[0].click().run()

    assert not at.exception
    assert at.session_state["auth_user"] is None
