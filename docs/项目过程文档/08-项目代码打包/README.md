# 08 项目代码打包

> 对应补充交付要求：**8. 项目代码打包**
> 当前状态：已按 v1.2 重建并完成解压验证（2026-11-20）
> 最终文件：`项目代码打包.zip`

---

## 1. 打包时间

代码实现（M1-M4.5）、测试（M5）与 README 定稿（M6）全部完成后执行。

## 2. 打包内容

必须包含：

- `app.py`
- `api/`（含导出的 `api/openapi.json`）
- `core/`
- `services/`
- `views/`
- `scripts/`
- `tests/`
- `docs/`（项目介绍文档与 01-11 过程文档、截图）
- `.streamlit/config.toml`
- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt`
- `.gitignore`
- `README.md`

必须排除：

- `.venv/`
- `data/*.db`
- `uploads/` 中的真实附件
- `.streamlit/secrets.toml`
- `docs/内部文档/`（D-03：内部文档不提交）
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.git/`

## 3. 打包命令

本项目实际使用 .NET `ZipFile` 按排除规则打包（比 `Compress-Archive` 更适合精确排除），核心规则：

```powershell
$excludePrefixes = @('.venv/', '.git/', '.pytest_cache/', '.ruff_cache/',
                     'data/', 'uploads/', 'docs/内部文档/')
# 逐个文件写入 zip，跳过上述前缀、__pycache__ 与 *.db / *.pyc
```

生成结果：

| 项 | 值 |
|---|---|
| 文件数 | 124 |
| 大小 | 约 487 KB |
| 含 `api/openapi.json` | 是 |
| 含 `.venv/`、`data/*.db`、`docs/内部文档/` | 否 |

## 4. 打包后验收

| 检查项 | 通过标准 | 结果 |
|---|---|---|
| 文件命名 | 必须为 `项目代码打包.zip` | ✅ |
| 无虚拟环境 | 解压后不存在 `.venv/` | ✅ |
| 无本地数据 | 不存在 `data/*.db` | ✅ |
| 无真实附件 | 不存在 `uploads/` 下的简历与营业执照 | ✅ |
| 无密钥 | 不存在 `.streamlit/secrets.toml` | ✅ |
| 无内部文档 | 不存在 `docs/内部文档/` | ✅ |
| REST 契约 | 存在 `api/openapi.json` | ✅ |
| 可运行 | 解压后按 README 可启动 | ✅ 解压后 146 个测试全部通过 |
| 文档齐全 | `docs/` 中过程文档（01-15）与项目介绍文档齐全 | ✅ |

## 5. 交付状态

| 项 | 状态 |
|---|---|
| 打包脚本 | 已写入手册 |
| 实际 zip | ✅ 已生成 |
| 解压验证 | ✅ 已完成（临时目录运行 pytest 通过） |
