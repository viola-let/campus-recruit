"""公网部署入口：首次启动自动建库并导入演示数据，然后加载主应用。

本地开发仍使用 `streamlit run app.py`；
Streamlit Community Cloud 等使用临时磁盘的环境，请把入口文件设为 `deploy_app.py`。
"""

import runpy
from pathlib import Path

from core.bootstrap import ensure_database

ensure_database()
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
