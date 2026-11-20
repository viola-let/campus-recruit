"""公网部署首次启动引导：建库并在空库时导入演示数据。

Streamlit Community Cloud 等免费环境使用临时磁盘，重启或重新部署后
`data/app.db` 可能丢失。本模块在应用入口幂等执行：
- 已有用户数据：只做建表 / 补列迁移，不覆盖任何数据；
- 空库：自动导入模拟演示数据，保证公网页面首次打开即可演示。
"""

from pathlib import Path

from core.db import get_connection, init_db, query_one


def ensure_database(db_path: Path | str | None = None) -> bool:
    """确保数据库可用；返回是否执行了演示数据导入。"""
    init_db(db_path)
    with get_connection(db_path) as conn:
        total = query_one(conn, "SELECT COUNT(*) AS total FROM users")["total"]
    if total:
        return False

    from scripts.seed_test_data import seed

    seed(db_path)
    return True
