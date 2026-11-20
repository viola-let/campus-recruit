"""兼容性与工程规范测试：版本、分层依赖、页面规模与配置。"""

import ast
import importlib.metadata
import sys
from pathlib import Path

from core.config import now_iso
from core.db import get_connection

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_python_version_compatible(db_path):
    """TC-K01：Python 版本处于 Streamlit 1.67 支持区间。"""
    assert (3, 11) <= sys.version_info[:2] <= (3, 14)


def test_runtime_versions_match_requirements(db_path):
    """TC-K02：锁定版本与当前环境安装版本一致。"""
    expected = {}
    for line in (
        (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    ):
        line = line.strip()
        if line and not line.startswith("#") and "==" in line:
            name, version = line.split("==", 1)
            expected[name.strip().lower()] = version.strip()

    for name in ("streamlit", "fastapi", "uvicorn", "pyjwt"):
        assert name in expected, f"requirements.txt 缺少 {name}"
        assert importlib.metadata.version(name) == expected[name]


def test_services_and_core_do_not_import_web_layers(db_path):
    """TC-K03：services/core 不依赖 Streamlit 或 FastAPI。"""
    forbidden = {"streamlit", "fastapi"}
    for directory in ("core", "services"):
        for path in (PROJECT_ROOT / directory).rglob("*.py"):
            modules = _imported_modules(path)
            assert not (modules & forbidden), f"{path} 引入了 Web 层依赖"


def test_views_and_api_do_not_access_database_directly(db_path):
    """TC-K04：表现层与 API 层不直接使用 sqlite3 / core.db。"""
    for directory in ("views", "api"):
        for path in (PROJECT_ROOT / directory).rglob("*.py"):
            modules = _imported_modules(path)
            assert "sqlite3" not in modules, f"{path} 直接导入了 sqlite3"
            assert "core.db" not in modules, f"{path} 绕过了服务层访问数据库"


def test_view_pages_are_small_enough(db_path):
    """TC-K05：单个页面文件不超过 250 行。"""
    for path in (PROJECT_ROOT / "views").rglob("*.py"):
        lines = path.read_text(encoding="utf-8").count("\n") + 1
        assert lines <= 250, f"{path} 共 {lines} 行，超过 250 行"


def test_app_uses_official_navigation(db_path):
    """TC-K06：入口使用官方 st.navigation + st.Page。"""
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.navigation" in source
    assert "st.Page" in source


def test_views_do_not_render_raw_html(db_path):
    """TC-K07：页面未使用 unsafe_allow_html，降低 XSS 风险。"""
    for path in (PROJECT_ROOT / "views").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "unsafe_allow_html" not in source, f"{path} 使用了原始 HTML"


def test_gitignore_covers_sensitive_files(db_path):
    """TC-K08：忽略本地数据库、上传目录、环境变量与密钥。"""
    ignored = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("data/", "uploads/", ".env", "secrets.toml"):
        assert pattern in ignored


def test_database_constraints_exist(db_path):
    """TC-K09：投递唯一约束、状态 CHECK 与索引存在。"""
    with get_connection() as conn:
        index_rows = conn.execute("PRAGMA index_list('applications')").fetchall()
        unique_columns = set()
        for row in index_rows:
            if row["unique"]:
                for info in conn.execute(
                    f"PRAGMA index_info('{row['name']}')"
                ).fetchall():
                    unique_columns.add(info["name"])

        job_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
        ).fetchone()["sql"]
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }

    assert {"job_id", "student_id"} <= unique_columns
    assert "CHECK" in job_sql
    assert {"idx_jobs_status", "idx_applications_stu"} <= indexes


def test_timestamp_uses_china_timezone(db_path):
    """TC-K10：时间戳为带 +08:00 的 ISO 8601 字符串。"""
    timestamp = now_iso()
    assert timestamp.endswith("+08:00")
