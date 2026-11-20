"""pytest 公共夹具：每个测试使用独立临时数据库。"""

import pytest

from core.db import init_db


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    """创建临时数据库，并通过环境变量让被测代码连接它。"""
    path = tmp_path / "test.db"
    monkeypatch.setenv("CAMPUS_DB_PATH", str(path))
    init_db(path)
    return path
