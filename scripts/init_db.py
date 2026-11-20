"""初始化数据库与平台管理员。

用法：
    python scripts/init_db.py --admin-email admin@example.com \
        --admin-password "ChangeMe123"
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.auth import create_admin  # noqa: E402
from core.db import get_connection, init_db, query_one  # noqa: E402
from core.errors import BusinessError  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化 CampusRecruit 数据库")
    parser.add_argument("--admin-email", required=True, help="管理员邮箱")
    parser.add_argument("--admin-password", required=True, help="管理员密码")
    parser.add_argument("--admin-name", default="平台管理员", help="管理员显示名称")
    args = parser.parse_args()

    init_db()

    email = args.admin_email.strip().lower()
    with get_connection() as conn:
        existing = query_one(conn, "SELECT id FROM users WHERE email = ?", (email,))

    if existing is not None:
        print(f"管理员已存在，跳过创建：{email}")
        return

    try:
        create_admin(email, args.admin_password, args.admin_name)
    except BusinessError as exc:
        print(f"创建管理员失败：{exc.message}")
        raise SystemExit(1) from exc

    print(f"数据库已初始化，管理员已创建：{email}")


if __name__ == "__main__":
    main()
