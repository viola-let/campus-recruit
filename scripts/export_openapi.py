"""导出 OpenAPI 契约到 api/openapi.json。

用法：
    python scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.main import app  # noqa: E402


def main() -> None:
    output_path = PROJECT_ROOT / "api" / "openapi.json"
    output_path.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI 契约已导出：{output_path}")


if __name__ == "__main__":
    main()
