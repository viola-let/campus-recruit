# 技术架构说明书（含 API 设计、数据库设计）

> 项目：校招平台 CampusRecruit
> 文档版本：v1.2（2026-11-18）
> 对应流程：图 2 阶段 3「技术设计文档（TDD）」
> 文档范围：技术选型、分层架构、**服务层 API + REST/OpenAPI 设计**、**数据库设计**、关键流程、安全、测试与部署
> 上游文档：[功能规格说明书 Spec](02-功能规格说明书.md)
> 技术基线：Python 3.12.x + Streamlit 1.67.0 + FastAPI 0.163.2 + SQLite（标准库）

---

## 1. 技术选型与依据

| 决策项 | 选择 | 依据 | 被否方案及原因 |
|---|---|---|---|
| 运行语言 | Python 3.12.x | Streamlit 1.67 官方支持 3.11-3.15 | 3.10 已不被支持；3.15 生态兼容风险略高 |
| Web 框架 | Streamlit 1.67.0 | 官方最新稳定版，原生支持多页、表单、会话状态、测试 | Flask/Django 需要额外前端与路由，超出初学者范围 |
| REST 适配器 | FastAPI 0.163.2 | 与 `services/` 共用业务核心，自动生成 OpenAPI 3.1 | 手写 Flask 路由需自行维护文档；仅内部契约无法对外提供 HTTP 接口 |
| API 认证 | PyJWT 2.15.1（HS256） | 轻量、标准、易测试，Token 可无状态校验 | 自建 Token 格式不安全；HTTP Basic 每次请求都传密码 |
| 多页方案 | `st.Page` + `st.navigation` | 官方“首选”方案，可按角色动态生成导航 | `pages/` 目录方案无法按角色动态裁剪 |
| 数据库 | SQLite（`sqlite3` 标准库） | 零安装、单文件、支持事务与唯一约束 | MySQL/PostgreSQL 需要额外服务；ORM 增加抽象负担 |
| 数据访问 | 手写参数化 SQL + `sqlite3.Row` | 学会 SQL 基础，无额外依赖，行为透明 | SQLAlchemy 对本项目规模偏重 |
| 密码哈希 | `hashlib.pbkdf2_hmac` + 随机盐 | Python 官方标准库，足够安全，无第三方依赖 | 明文/简单 MD5 不安全；bcrypt 增加依赖 |
| 文件存储 | 本地 `uploads/` + UUID 文件名 | MVP 简单可演示 | 对象存储需要云账号与 SDK |
| 测试 | pytest + `streamlit.testing.v1.AppTest` | Streamlit 官方原生测试框架，官方推荐配合 pytest | Selenium/Playwright 对课程项目过重 |
| 代码质量 | ruff（PEP 8） | Python 社区通用、速度快、配置简单 | flake8 + black + isort 需要三套工具 |
| 配置 | `.streamlit/config.toml` | 官方项目级配置方式 | 自定义配置系统不符合官方标准 |

---

## 2. 架构设计

### 2.1 运行架构（官方客户端-服务端模型）

```text
┌──────────────────────┐        ┌──────────────────────┐
│ 浏览器（Streamlit UI）│        │ API 客户端 / Swagger │
└──────────┬───────────┘        └──────────┬───────────┘
           │ WebSocket                      │ HTTP
┌──────────▼───────────┐        ┌──────────▼───────────┐
│ Streamlit Server     │        │ FastAPI Server       │
│ app.py + views/      │        │ api/main.py + routes │
└──────────┬───────────┘        └──────────┬───────────┘
           └──────────────┬─────────────────┘
                          ▼
                 services/（业务规则）
                          ▼
                 core/（数据库 / 安全 / 配置）
                          ▼
                 data/app.db + uploads/
```

两个入口共用同一套 `services/`，避免业务规则重复。Streamlit 与 FastAPI 可以是两个独立进程，也可以在本地分别启动。

必须记住的两条官方结论：

1. **所有用户共享同一个 Python 服务端进程**，计算与文件都发生在服务器，不在浏览器。
2. **每个浏览器标签页有独立会话**，登录态必须放在 `st.session_state`，不能放在模块级全局变量。

### 2.2 代码分层

```text
views/（Streamlit 表现层）        api/（REST 适配层）
        │                              │
        └──────────────┬───────────────┘
                       ▼
                services/（业务层）
                       ▼
                core/（基础设施层）
                       ▼
                SQLite + 本地文件
```

| 层 | 允许导入 | 禁止导入 | 可测试性 |
|---|---|---|---|
| `views/` | `streamlit`、`services`、`core.config` | 直接 `sqlite3` | 通过 AppTest 测试 |
| `api/` | `fastapi`、`services`、`core.config` | `streamlit`、直接 `sqlite3` | 通过 TestClient / pytest 测试 |
| `services/` | `core`、标准库 | **`streamlit`**、`fastapi` | 可直接用 pytest 测试 |
| `core/` | 标准库 | `streamlit`、`fastapi`、`services`、`views`、`api` | 可直接用 pytest 测试 |

> 关键约束：`services/` 不导入 Streamlit 或 FastAPI，这样同一套业务规则可以被两个入口复用，也能在没有 UI 的情况下测试。

### 2.3 依赖方向

```text
app.py ──► views/* ──┐
                     ├──► services/* ──► core/*
api/main.py ─► api/routes/* ─┘
```

禁止反向依赖，禁止循环导入。

---

## 3. 模块职责

| 文件 | 职责 | 关键函数（阶段 5 实现） |
|---|---|---|
| `app.py` | 初始化会话、构建导航、全局侧边栏、执行页面 | `main()` |
| `core/config.py` | 路径、枚举、会话 key、业务常量 | `Role`、`ReviewStatus`、`JobStatus`、`ApplicationStatus` |
| `core/db.py` | 连接管理、建表、事务、查询辅助 | `get_connection()`、`init_db()`、`query_one()`、`query_all()` |
| `core/security.py` | 密码哈希与校验、文件校验、UUID 文件名 | `hash_password()`、`verify_password()`、`validate_upload()` |
| `core/auth.py` | 注册、登录、当前用户、角色校验 | `register_student()`、`register_company()`、`login()`、`require_role()` |
| `services/companies.py` | 企业资料、双审核状态、职位发布资格 | `upsert_profile()`、`can_publish_job()`、`review_license()`、`review_hr()` |
| `services/jobs.py` | 职位创建、检索、审核、关闭、推荐 | `create_job()`、`search_jobs()`、`review_job()`、`close_job()` |
| `services/students.py` | 简历保存、附件、送审、核查 | `save_resume()`、`get_resume()`、`review_resume()` |
| `services/applications.py` | 投递、快照、状态流转、反馈 | `apply_to_job()`、`list_my_applications()`、`list_job_candidates()`、`update_status()` |
| `services/admin.py` | 统计与待办查询 | `dashboard_counts()`、`pending_queues()` |
| `api/main.py` | FastAPI 实例、CORS、路由注册、健康检查 | `app`、`/health` |
| `api/deps.py` | Bearer Token 解析、当前用户、角色守卫 | `get_current_user()`、`require_role()` |
| `api/schemas.py` | Pydantic 请求 / 响应模型 | `LoginRequest`、`TokenResponse`、`JobCreate` |
| `api/routes/*.py` | 认证、学生、企业、职位、投递、管理端路由 | 见 6.5.7 端点清单 |
| `scripts/init_db.py` | 建库、建表、创建管理员 | `main()` |
| `scripts/export_openapi.py` | 导出 `openapi.json` 交付文件 | `main()` |

---

## 4. 数据模型

### 4.1 实体关系

```text
users 1 ─── 0..1 companies
users 1 ─── 0..1 resumes
companies 1 ─── * jobs
jobs 1 ─── * applications
users(student) 1 ─── * applications
resumes 1 ─── * applications（投递时保存快照）
users(admin) 1 ─── * review_logs
```

### 4.2 建表语句（SQLite）

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('student', 'company', 'admin')),
    display_name  TEXT    NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    license_no    TEXT    NOT NULL,
    license_file  TEXT,
    hr_name       TEXT    NOT NULL,
    hr_email      TEXT    NOT NULL,
    hr_proof_file TEXT,
    status        TEXT    NOT NULL DEFAULT 'PENDING'
                  CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    hr_status     TEXT    NOT NULL DEFAULT 'PENDING'
                  CHECK (hr_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title        TEXT    NOT NULL,
    job_type     TEXT    NOT NULL CHECK (job_type IN ('CAMPUS', 'INTERN')),
    city         TEXT    NOT NULL,
    salary       TEXT,
    description  TEXT    NOT NULL,
    requirements TEXT,
    status       TEXT    NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CLOSED')),
    is_featured  INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    real_name       TEXT    NOT NULL,
    phone           TEXT    NOT NULL,
    school          TEXT    NOT NULL,
    major           TEXT    NOT NULL,
    graduation_year INTEGER NOT NULL,
    skills          TEXT,
    summary         TEXT,
    file_path       TEXT,
    status          TEXT    NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'VERIFIED', 'REJECTED')),
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id               INTEGER NOT NULL REFERENCES jobs(id),
    student_id           INTEGER NOT NULL REFERENCES users(id),
    resume_id            INTEGER NOT NULL REFERENCES resumes(id),
    resume_snapshot      TEXT    NOT NULL,
    resume_file_snapshot TEXT,
    status               TEXT    NOT NULL DEFAULT 'SUBMITTED'
                         CHECK (status IN ('SUBMITTED', 'VIEWED', 'SHORTLISTED', 'REJECTED', 'HIRED')),
    feedback             TEXT,
    created_at           TEXT    NOT NULL,
    updated_at           TEXT    NOT NULL,
    UNIQUE (job_id, student_id)
);

CREATE TABLE IF NOT EXISTS review_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT    NOT NULL
                CHECK (entity_type IN ('company_license', 'company_hr', 'job', 'resume')),
    entity_id   INTEGER NOT NULL,
    decision    TEXT    NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED', 'VERIFIED')),
    note        TEXT,
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    created_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status        ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_company       ON jobs (company_id);
CREATE INDEX IF NOT EXISTS idx_applications_job   ON applications (job_id);
CREATE INDEX IF NOT EXISTS idx_applications_stu   ON applications (student_id);
CREATE INDEX IF NOT EXISTS idx_review_entity      ON review_logs (entity_type, entity_id);
```

### 4.3 设计说明

| 设计点 | 原因 |
|---|---|
| 邮箱 `COLLATE NOCASE` | 避免 `A@x.com` 与 `a@x.com` 重复注册 |
| 审核状态用 `CHECK` 约束 | 数据库层兜底，防止写入非法状态 |
| 投递表 `UNIQUE(job_id, student_id)` | 从数据层保证“不可重复投递” |
| `resume_snapshot` | 企业看到的是投递当时的内容，学生后续修改不影响历史记录 |
| `review_logs` 独立表 | 四层审核共用审计结构，可追溯审核人、时间、理由 |
| 状态与日志分离 | 当前状态查询快；历史记录完整 |
| 时间存 ISO 8601 文本 | SQLite 无原生日期类型，ISO 文本可直接排序比较 |
| 软状态代替物理删除 | 职位用 `CLOSED`、审核用 `REJECTED`，避免破坏投递记录 |

---

## 5. 数据库访问设计

### 5.1 连接策略

**每次操作打开一个短连接，用完立即关闭；不使用模块级全局连接。**

原因：

- 每个浏览器标签页是独立会话，模块级连接会在多个会话间共享，产生线程安全问题；
- SQLite 连接不应跨线程复用；
- 短连接实现简单，事务边界清晰，适合初学者。

```python
# core/db.py（示意）
import sqlite3
from contextlib import contextmanager


@contextmanager
def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 5.2 查询规范

- 一律 `conn.execute(sql, params)` 参数化，禁止 f-string 拼 SQL。
- 单行用 `query_one()` 返回 `dict | None`；多行用 `query_all()` 返回 `list[dict]`。
- 列表查询必须带 `ORDER BY` 与 `LIMIT`（默认 100）。
- 写操作返回业务对象或抛出 `BusinessError`。

### 5.3 事务边界

| 操作 | 事务范围 |
|---|---|
| 企业注册 | 插入 `users` + 插入 `companies` 同一事务 |
| 投递 | 校验 + 插入 `applications` 同一事务 |
| 审核 | 读取状态 + 更新状态 + 插入 `review_logs` 同一事务 |
| 状态流转 | 读取当前状态 + 条件更新 + 更新 `updated_at` 同一事务 |

---

## 6. 关键流程设计

### 6.1 登录

```text
登录表单
  → auth.login(email, password)
      → 按邮箱查 users
      → 校验 is_active
      → verify_password(明文, 存储哈希)
      → 返回用户字典（不含密码哈希）
  → st.session_state["auth_user"] = user
  → st.rerun()
```

失败统一返回“邮箱或密码错误”，不区分账号是否存在。

### 6.2 学生投递

```text
点击投递
  → applications.apply_to_job(student_id, job_id)
      1. 读取简历，状态必须为 VERIFIED
      2. 读取职位，状态必须为 APPROVED
      3. 查询是否已投递 → 已存在则报错
      4. 生成简历快照 JSON + 附件路径快照
      5. 插入 applications（SUBMITTED）
  → st.success + st.rerun()
```

### 6.3 企业处理投递

```text
选择候选人 + 新状态 + 反馈
  → applications.update_status(actor, application_id, new_status, feedback)
      1. 校验 actor.role == company
      2. 通过 application → job → company 校验归属
      3. 校验状态流转是否在允许表内
      4. 若目标为 REJECTED，反馈必填
      5. 更新状态与 updated_at
```

### 6.4 管理员审核（以职位为例）

```text
审核表单
  → services.jobs.review_job(admin_id, job_id, decision, note)
      1. 校验 actor.role == admin
      2. 事务内读取职位，状态必须为 PENDING
      3. 更新 jobs.status
      4. 插入 review_logs(entity_type='job')
      5. 返回最新职位
```

第 2 步在事务内重新读取状态，避免两个管理员同时审核导致覆盖。

### 6.5 服务层 API 与 REST 接口设计

#### 6.5.1 两层 API：内部服务契约 + REST 适配器

本项目有两层 API：

| 层 | 形式 | 调用方 | 作用 |
|---|---|---|---|
| 内部服务 API | `services/` 中的 Python 函数 | Streamlit 页面、FastAPI 路由、pytest | 业务规则的唯一实现 |
| REST API | FastAPI 路由 `/api/v1/*` | Swagger、第三方客户端、接口测试 | 对外提供 HTTP + JSON 接口，自动生成 OpenAPI |

约束：

- `services/` 不导入 Streamlit，也不导入 FastAPI；
- `views/` 与 `api/routes/` 都只调用 `services/`，不直接写 SQL；
- 两个入口共用同一套权限与状态机，禁止在路由中复制业务规则；
- REST 文档由 FastAPI 自动生成，不手写第二份 Swagger。

#### 6.5.2 统一约定

| 约定 | 规则 |
|---|---|
| 命名 | 动词 + 名词，如 `apply_to_job`、`review_job` |
| 受保护操作 | 第一个参数固定为 `actor_id: int`（当前登录用户 ID） |
| 入参 | 使用普通 `dict` 或基础类型，不暴露数据库连接 |
| 返回 | `dict`、`list[dict]`、`bool` 或 `None`；**绝不返回 `password_hash`** |
| 异常 | 业务失败抛出 `BusinessError(code, message)`；未知异常向上抛出 |
| 事务 | 涉及多表写入的函数内部使用同一连接与事务 |
| 时间 | 统一写入 `Asia/Shanghai` 的 ISO 8601 字符串 |
| 分页 | `limit` 默认 100，最大 200；列表必须指定 `ORDER BY` |
| 权限 | 角色校验 + 资源归属校验都在函数内部完成 |

```python
# core/errors.py（阶段 5 实现）
class BusinessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
```

#### 6.5.3 错误码

| code | 含义 | 页面提示示例 |
|---|---|---|
| `VALIDATION_ERROR` | 字段校验失败 | 请检查必填项 |
| `EMAIL_EXISTS` | 邮箱已注册 | 该邮箱已注册，请直接登录 |
| `AUTH_INVALID_CREDENTIALS` | 邮箱或密码错误 | 邮箱或密码错误 |
| `AUTH_INACTIVE` | 账号被停用 | 账号已停用，请联系管理员 |
| `FORBIDDEN` | 角色或归属不匹配 | 无权限执行该操作 |
| `NOT_FOUND` | 资源不存在 | 记录不存在或已被删除 |
| `INVALID_STATE` | 状态流转非法 | 当前状态不允许该操作 |
| `RESUME_NOT_VERIFIED` | 简历未通过核查 | 简历通过核查后才能投递 |
| `JOB_NOT_OPEN` | 职位不可投递 | 该职位已关闭或未通过审核 |
| `DUPLICATE_APPLICATION` | 重复投递 | 请勿重复投递 |
| `FILE_INVALID` | 文件类型不合法 | 仅支持 PDF / DOCX |
| `FILE_TOO_LARGE` | 文件超过限制 | 文件不能超过 5 MB |

#### 6.5.4 API 清单

**认证与用户（`core/auth.py`）**

| 函数 | 权限 | 入参 | 返回 | 主要错误 |
|---|---|---|---|---|
| `register_student(email, password, display_name)` | 公开 | 邮箱、密码、姓名 | `user_id` | `EMAIL_EXISTS`、`VALIDATION_ERROR` |
| `register_company(email, password, company_name)` | 公开 | 邮箱、密码、企业名 | `user_id` | `EMAIL_EXISTS`、`VALIDATION_ERROR` |
| `login(email, password)` | 公开 | 邮箱、密码 | 用户字典（不含哈希） | `AUTH_INVALID_CREDENTIALS`、`AUTH_INACTIVE` |
| `get_user(user_id)` | 已登录 | 用户 ID | 用户字典或 `None` | — |
| `require_role(actor_id, role)` | 已登录 | 用户 ID、角色 | `dict` | `FORBIDDEN`、`AUTH_INACTIVE` |

**学生与简历（`services/students.py`）**

| 函数 | 权限 | 入参 | 返回 | 主要错误 |
|---|---|---|---|---|
| `get_resume(actor_id, student_id=None)` | 学生本人 / 管理员 | 学生 ID（管理员必填） | 简历字典或 `None` | `FORBIDDEN` |
| `save_resume(actor_id, payload)` | 学生 | 姓名、手机号、学校、专业、毕业年份、技能、简介 | 简历字典（状态 `PENDING`） | `VALIDATION_ERROR` |
| `attach_resume_file(actor_id, filename, content)` | 学生 | 文件名、字节内容 | 相对路径 | `FILE_INVALID`、`FILE_TOO_LARGE` |
| `review_resume(admin_id, resume_id, decision, note)` | 管理员 | 简历 ID、决策、备注 | 最新简历 | `FORBIDDEN`、`INVALID_STATE` |
| `list_pending_resumes(admin_id, limit=100)` | 管理员 | 管理员 ID、数量 | 简历列表 | `FORBIDDEN` |

**企业与审核（`services/companies.py`）**

| 函数 | 权限 | 入参 | 返回 | 主要错误 |
|---|---|---|---|---|
| `get_profile(actor_id, user_id=None)` | 企业本人 / 管理员 | 企业账号 ID（管理员可指定） | 企业字典或 `None` | `FORBIDDEN` |
| `upsert_profile(actor_id, payload)` | 企业 | 企业名、信用代码、HR 姓名、HR 邮箱 | 企业字典（状态回 `PENDING`） | `VALIDATION_ERROR` |
| `attach_company_file(actor_id, kind, filename, content)` | 企业 | `license` / `hr_proof`、文件 | 相对路径 | `FILE_INVALID`、`FILE_TOO_LARGE` |
| `can_publish_job(actor_id)` | 企业 | 企业账号 ID | `bool` | — |
| `review_license(admin_id, company_id, decision, note)` | 管理员 | 企业 ID、决策、备注 | 最新企业记录 | `FORBIDDEN`、`INVALID_STATE` |
| `review_hr(admin_id, company_id, decision, note)` | 管理员 | 企业 ID、决策、备注 | 最新企业记录 | `FORBIDDEN`、`INVALID_STATE` |
| `set_company_active(admin_id, company_id, active)` | 管理员 | 企业 ID、是否启用 | `None` | `FORBIDDEN` |
| `list_pending_companies(admin_id, limit=100)` | 管理员 | 管理员 ID、数量 | 企业列表 | `FORBIDDEN` |

**职位（`services/jobs.py`）**

| 函数 | 权限 | 入参 | 返回 | 主要错误 |
|---|---|---|---|---|
| `create_job(actor_id, payload)` | 企业（双审通过） | 标题、类型、城市、薪资、描述、要求 | 职位字典（`PENDING`） | `FORBIDDEN`、`VALIDATION_ERROR` |
| `update_job(actor_id, job_id, payload)` | 职位所属企业 | 职位 ID、字段 | 职位字典（`PENDING`） | `FORBIDDEN`、`INVALID_STATE` |
| `close_job(actor_id, job_id)` | 职位所属企业 | 职位 ID | `None` | `FORBIDDEN`、`INVALID_STATE` |
| `reopen_job(actor_id, job_id)` | 职位所属企业 | 职位 ID | 职位字典（`PENDING`） | `FORBIDDEN`、`INVALID_STATE` |
| `search_jobs(keyword=None, city=None, job_type=None, limit=100)` | 学生 / 管理员 | 筛选条件 | 已通过职位列表 | — |
| `list_company_jobs(actor_id, limit=100)` | 企业 | 企业账号 ID | 本公司职位列表 | `FORBIDDEN` |
| `review_job(admin_id, job_id, decision, note)` | 管理员 | 职位 ID、决策、备注 | 最新职位 | `FORBIDDEN`、`INVALID_STATE` |
| `set_featured(admin_id, job_id, featured)` | 管理员 | 职位 ID、是否推荐 | `None` | `FORBIDDEN`、`INVALID_STATE` |
| `list_pending_jobs(admin_id, limit=100)` | 管理员 | 管理员 ID、数量 | 职位列表 | `FORBIDDEN` |

**投递（`services/applications.py`）**

| 函数 | 权限 | 入参 | 返回 | 主要错误 |
|---|---|---|---|---|
| `apply_to_job(actor_id, job_id)` | 学生 | 职位 ID | 投递记录 | `RESUME_NOT_VERIFIED`、`JOB_NOT_OPEN`、`DUPLICATE_APPLICATION` |
| `list_my_applications(actor_id)` | 学生 | 学生 ID | 投递列表（含反馈） | — |
| `list_job_candidates(actor_id, filters, limit=100)` | 企业 | 职位、学校、专业、状态 | 候选人列表（含简历快照） | `FORBIDDEN` |
| `update_status(actor_id, application_id, new_status, feedback=None)` | 职位所属企业 | 投递 ID、新状态、反馈 | 最新投递记录 | `FORBIDDEN`、`INVALID_STATE`、`VALIDATION_ERROR` |
| `get_resume_file(actor_id, application_id)` | 职位所属企业 / 管理员 | 投递 ID | `(文件名, bytes)` | `FORBIDDEN`、`NOT_FOUND` |

**管理端统计（`services/admin.py`）**

| 函数 | 权限 | 入参 | 返回 | 主要错误 |
|---|---|---|---|---|
| `dashboard_counts(admin_id)` | 管理员 | 管理员 ID | 6 项指标字典 | `FORBIDDEN` |
| `pending_queues(admin_id, limit=20)` | 管理员 | 管理员 ID、数量 | 四类待办列表字典 | `FORBIDDEN` |

#### 6.5.5 返回结构约定

| 对象 | 必含字段 | 禁止字段 |
|---|---|---|
| 用户 | `id`、`email`、`role`、`display_name`、`is_active` | `password_hash` |
| 简历 | `id`、`student_id`、`real_name`、`school`、`major`、`graduation_year`、`status`、`updated_at` | — |
| 职位 | `id`、`company_id`、`company_name`、`title`、`job_type`、`city`、`status`、`is_featured` | — |
| 投递 | `id`、`job_id`、`job_title`、`company_name`、`status`、`feedback`、`resume_snapshot`、`updated_at` | — |

#### 6.5.6 接口级权限原则

1. **角色**：学生不能调用企业/管理员函数，反之亦然。
2. **归属**：企业只能操作自己的职位与投递；学生只能操作自己的简历与投递。
3. **状态**：审核类接口只接受 `PENDING`；投递状态接口只接受 Spec 5.3 允许的流转。
4. **展示与校验分离**：页面隐藏按钮只改善体验，不作为安全边界。

#### 6.5.7 REST API 端点（`/api/v1`）

**认证**

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/v1/auth/register/student` | 公开 | 学生注册 |
| POST | `/api/v1/auth/register/company` | 公开 | 企业注册 + 创建待审资料 |
| POST | `/api/v1/auth/login` | 公开 | 返回 `access_token`、`token_type`、`expires_in` |
| GET | `/api/v1/auth/me` | 已登录 | 返回当前用户（不含密码哈希） |

**学生**

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/v1/students/me/resume` | 学生 | 查看本人简历 |
| PUT | `/api/v1/students/me/resume` | 学生 | 保存简历，状态回 `PENDING` |
| POST | `/api/v1/students/me/resume/file` | 学生 | `multipart/form-data` 上传附件 |
| GET | `/api/v1/students/me/applications` | 学生 | 我的投递与反馈 |

**职位与投递**

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/v1/jobs` | 学生 / 管理员 | 关键词、城市、类型筛选，仅返回 `APPROVED` |
| POST | `/api/v1/jobs/{job_id}/applications` | 学生 | 投递，校验简历与重复投递 |

**企业**

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/v1/companies/me` | 企业 | 企业资料与双审核状态 |
| PUT | `/api/v1/companies/me` | 企业 | 更新资料，状态回 `PENDING` |
| POST | `/api/v1/companies/me/files/{kind}` | 企业 | `kind` = `license` / `hr_proof` |
| GET | `/api/v1/companies/me/jobs` | 企业 | 本公司职位 |
| POST | `/api/v1/companies/me/jobs` | 企业（双审通过） | 发布职位 |
| PATCH | `/api/v1/companies/me/jobs/{job_id}` | 职位所属企业 | 编辑 / 关闭 / 重开 |
| GET | `/api/v1/companies/me/candidates` | 企业 | 按职位、学校、专业、状态筛选 |
| PATCH | `/api/v1/applications/{application_id}/status` | 职位所属企业 | 状态流转 + 反馈 |
| GET | `/api/v1/applications/{application_id}/resume-file` | 职位所属企业 / 管理员 | 下载投递快照附件 |

**管理员**

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/api/v1/admin/dashboard` | 管理员 | 6 项指标 |
| GET | `/api/v1/admin/pending` | 管理员 | 四类待办队列 |
| POST | `/api/v1/admin/companies/{company_id}/license/review` | 管理员 | 企业资质审核 |
| POST | `/api/v1/admin/companies/{company_id}/hr/review` | 管理员 | 企业 HR 审核 |
| POST | `/api/v1/admin/jobs/{job_id}/review` | 管理员 | 职位审核 / 推荐 |
| POST | `/api/v1/admin/resumes/{resume_id}/review` | 管理员 | 简历核查 |

**Token 与错误约定**

| 项 | 规则 |
|---|---|
| Token 类型 | JWT（HS256），`Authorization: Bearer <token>` |
| Payload | `sub`（用户 ID）、`role`、`iat`、`exp`（8 小时） |
| 密钥 | 环境变量 `API_JWT_SECRET`；本地开发可用默认值，公网必须更换 |
| 未认证 | `401 Unauthorized` |
| 角色 / 归属不符 | `403 Forbidden` |
| 业务错误 | `BusinessError` 映射为 `400/404/409`，响应体 `{code, message}` |
| CORS | 允许 `http://localhost:8501`（Streamlit 本地调用） |
| Swagger | `/docs` |
| OpenAPI | `/openapi.json`（OpenAPI 3.1） |

> `openapi.json` 由 `scripts/export_openapi.py` 导出到 `api/openapi.json`，作为“API 设计”的可验证产物；不单独新增提交物编号。

---

## 7. Streamlit 实现规范

### 7.1 入口与路由

`app.py` 是唯一入口，负责初始化会话、按角色构建导航：

```python
# app.py（结构示意，阶段 5 实现）
import streamlit as st

st.set_page_config(page_title="校招平台", page_icon="🎓", layout="wide")

user = st.session_state.get("auth_user")

if user is None:
    page = st.navigation([st.Page("views/auth/login.py", title="登录 / 注册")])
else:
    if user["role"] == "student":
        pages = {
            "学生端": [
                st.Page("views/student/home.py", title="首页", default=True),
                st.Page("views/student/resume.py", title="我的简历"),
                st.Page("views/student/jobs.py", title="职位广场"),
                st.Page("views/student/applications.py", title="我的投递"),
            ]
        }
    elif user["role"] == "company":
        pages = {
            "企业端": [
                st.Page("views/company/home.py", title="首页", default=True),
                st.Page("views/company/profile.py", title="企业资料"),
                st.Page("views/company/jobs.py", title="职位管理"),
                st.Page("views/company/candidates.py", title="候选人"),
            ]
        }
    else:
        pages = {
            "管理端": [
                st.Page("views/admin/home.py", title="概览", default=True),
                st.Page("views/admin/companies.py", title="企业审核"),
                st.Page("views/admin/jobs.py", title="职位审核"),
                st.Page("views/admin/resumes.py", title="简历核查"),
            ]
        }
    page = st.navigation(pages)

# 全局侧边栏（入口文件中的元素对所有页面可见）
with st.sidebar:
    st.caption(f"当前用户：{user['display_name'] if user else '未登录'}")

page.run()
```

要点：

- `st.navigation` 每次运行只调用一次，且必须在入口文件；
- 返回的 `page` 必须调用 `.run()`；
- 入口文件中的侧边栏元素会成为所有页面的公共元素；
- 页面标题与图标通过 `st.Page` 的 `title` / `icon` 指定。

### 7.2 会话状态

| Key | 类型 | 说明 | 初始化位置 |
|---|---|---|---|
| `auth_user` | `dict \| None` | `id`、`email`、`role`、`display_name` | `app.py` |
| `flash` | `str \| None` | 跨页面一次性提示 | `app.py` |

规则：

- 所有 key 使用 `core/config.py` 中的常量，禁止散落字符串；
- 只存必要信息，**不存密码哈希**；
- 退出登录时清空整个 `st.session_state`；
- 不使用 URL 参数传递角色或用户 ID。

### 7.3 缓存策略

| 场景 | 是否缓存 | 做法 |
|---|---|---|
| 职位列表、审核队列 | 否（MVP） | 直接查库，保证审核后立即生效 |
| 平台统计数据 | 可选 | `@st.cache_data(ttl=30)` |
| 数据库连接 | 否 | 每次操作短连接 |
| 全局只读资源（如配置） | 可 | `@st.cache_resource` |

**硬性规则：任何写操作都不得经过 `st.cache_data`。** 写成功后如需刷新统计，调用 `st.cache_data.clear()`。

### 7.4 表单与重跑

- 3 个及以上输入 + 一个提交动作 → 使用 `st.form`；
- 表单提交成功后调用 `st.rerun()`，让列表与状态立即更新；
- 不在 `st.form` 内调用 `st.rerun()`；
- 每个页面内的控件 `key` 加页面前缀，避免跨页冲突（如 `student_jobs_keyword`）。

### 7.5 文件上传

```text
st.file_uploader(type=["pdf", "docx"])
  → 校验文件大小 ≤ 5 MB
  → 校验扩展名在白名单
  → 生成 UUID 文件名（保留原扩展名）
  → 保存到 uploads/licenses 或 uploads/resumes
  → 数据库只存相对路径
```

禁止：

- 使用用户原始文件名拼接路径；
- 允许 `exe`、`zip`、`html` 等可执行或可渲染格式；
- 将文件保存到 `uploads/` 之外的目录。

### 7.6 页面组织

| 规则 | 说明 |
|---|---|
| 页面脚本顶层执行 | 不写 `if __name__ == "__main__"` |
| 页面不写 SQL | 所有数据操作走 `services/` |
| 页面不写权限规则 | 只控制展示；真正校验在服务层 |
| 页面文件 ≤ 250 行 | 超出则拆分组件或服务函数 |
| 空状态 | 列表为空时给出下一步操作引导 |

---

## 8. 安全设计

| 风险 | 措施 |
|---|---|
| 密码泄露 | PBKDF2-HMAC-SHA256，随机 16 字节盐，迭代 600,000 次；存储格式 `pbkdf2_sha256$600000$<salt>$<hash>`（Base64） |
| 时序攻击 | 使用 `hmac.compare_digest` 比较哈希 |
| SQL 注入 | 全部参数化查询 |
| 越权 | 服务层校验角色 + 资源归属；页面隐藏按钮只是体验优化 |
| 文件上传 | 白名单 + 大小限制 + UUID 文件名 + 目录边界校验 |
| 路径穿越 | 使用 `Path.resolve()` 后确认父目录为 `uploads/` |
| 会话伪造 | 登录信息只存服务端 `st.session_state`，不接受前端传入的角色 |
| XSS | 用户内容默认转义；禁用 `unsafe_allow_html` |
| 信息泄露 | 登录失败提示统一；异常不向页面输出堆栈与路径 |
| 敏感配置 | `secrets.toml`、`data/*.db`、`uploads/**` 全部 gitignore |

> 生产环境补充（本 MVP 不做）：登录限流、CSRF 防护、OIDC 单点登录、审计告警。Streamlit 官方提供 `st.login()` 对接 OIDC，可作为后续升级路径。

---

## 9. 测试设计

### 9.1 测试分层

| 层级 | 文件 | 重点 |
|---|---|---|
| 单元测试 | `tests/test_security.py` | 哈希可验证、错误密码失败、上传校验 |
| 服务测试 | `tests/test_auth.py`、`tests/test_services.py` | 注册重复、登录停用、投递规则、状态流转、越权 |
| 页面冒烟 | `tests/test_app_smoke.py` | AppTest 加载登录页、登录后页面无异常 |

### 9.2 测试夹具

```python
# tests/conftest.py（示意）
import pytest

from core.db import init_db


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "test.db"
    init_db(path)
    return path
```

要求：

- 每个测试使用 `tmp_path` 下的独立数据库；
- 绝不读写 `data/app.db`；
- 上传测试使用 `tmp_path` 作为上传根目录。

### 9.3 必测清单

| 编号 | 用例 | 期望 |
|---|---|---|
| T-01 | 正确密码校验 | 返回 `True` |
| T-02 | 错误密码校验 | 返回 `False` |
| T-03 | 重复邮箱注册 | 抛出业务错误 |
| T-04 | 停用账号登录 | 拒绝 |
| T-05 | 未核查简历投递 | 拒绝 |
| T-06 | 重复投递 | 拒绝 |
| T-07 | 企业查看其他公司投递 | 拒绝 |
| T-08 | 非法状态流转 | 拒绝 |
| T-09 | 非管理员调用审核 | 拒绝 |
| T-10 | 上传超大文件 | 拒绝 |
| T-11 | AppTest 未登录进入登录页 | 页面包含登录表单 |
| T-12 | AppTest 学生登录后进入首页 | 无异常，导航含学生页面 |
| T-13 | REST 无 Token 访问受保护接口 | 返回 401 |
| T-14 | REST 学生 Token 调用管理端接口 | 返回 403 |
| T-15 | REST 登录后调用 `/auth/me` | 返回当前用户，且不含密码哈希 |

### 9.4 质量门禁

```powershell
ruff format --check .
ruff check .
python -m compileall .
pytest -q
```

四项全部通过才允许合并。

---

## 10. 部署设计

### 10.1 本地运行（本项目主场景）

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/init_db.py
streamlit run app.py                 # UI：http://localhost:8501
uvicorn api.main:app --reload --port 8000   # REST：http://localhost:8000/docs
```

两个进程共用同一份 `data/app.db` 与 `uploads/`，可以只启动 Streamlit，也可以只启动 FastAPI，或同时启动。浏览器访问 `http://localhost:8501`；REST 文档访问 `http://localhost:8000/docs`。

### 10.2 Streamlit Community Cloud（可选演示）

| 要求 | 做法 |
|---|---|
| 入口文件 | `app.py` |
| 依赖 | 根目录 `requirements.txt` |
| Python 版本 | 在部署设置中选择 3.12 |
| 密钥 | 在平台 Secrets 中配置，不提交 `secrets.toml` |

**两条重要限制：**

1. Community Cloud 的本地文件系统不是持久存储，SQLite 与 `uploads/` 可能在重启后丢失。因此本项目定位为**本地演示版**；若要长期在线，需要把数据库换成托管 PostgreSQL，把文件换成对象存储。
2. Community Cloud **只运行一个 Streamlit 进程**，无法同时拉起 FastAPI。因此：**公网 URL / 二维码只指向 Streamlit 演示页；REST 接口与 OpenAPI 文档只在本机（或自建 VPS/Docker）可用**，不作为公网可访问能力承诺。

---

## 11. 技术风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| SQLite 并发写锁 | 多人同时写可能短暂阻塞 | 控制演示并发 ≤ 20；必要时启用 WAL 模式 |
| 本地文件非持久 | 云端重启丢失数据 | 明确本地定位；升级路径为托管数据库 + 对象存储 |
| Session State 认证强度 | 不适合公网生产 | 仅本地演示；后续改用官方 `st.login()` OIDC |
| 页面重跑导致重复提交 | 可能重复写库 | 写操作加唯一约束 + 表单提交后 `st.rerun()` |
| 上传文件安全 | 恶意文件 | 白名单、大小限制、UUID 命名、目录边界校验 |
| 版本升级破坏 API | 运行失败 | 锁定 Streamlit 版本；升级单独提交并跑全量测试 |
| 业务逻辑写进页面 | 难测试、难维护 | 强制 `services/` 不导入 Streamlit；评审检查 |
| 中文排序/大小写 | 搜索结果异常 | 邮箱 `NOCASE`；关键词搜索统一 `LIKE` 参数化 |
| 双进程共享 SQLite | 两进程同时写可能锁表 | 控制演示并发；写操作短事务；必要时启用 WAL 模式 |
| JWT 密钥泄露 | 可伪造任意身份 | 公网必须更换 `API_JWT_SECRET`；不写入 Git；Token 有效期 8 小时 |
| CORS 配置过宽 | 任意站点可调用接口 | 仅允许 `http://localhost:8501`，不使用 `*` |
| 公网无法运行 REST | 验收时误判为缺失 | 文档明确写清：Community Cloud 只跑 Streamlit；REST 本地交付 |
| 两入口业务漂移 | Streamlit 与 REST 规则不一致 | 两者都只调用 `services/`，禁止各自复制业务逻辑 |

---

## 12. 版本约束汇总

| 项 | 约束 | 说明 |
|---|---|---|
| Python | `>=3.11,<3.16` | 与 Streamlit 1.67 官方支持范围一致 |
| Streamlit | `==1.67.0` | 精确锁定 |
| FastAPI | `==0.163.2` | 精确锁定，自动生成 OpenAPI 3.1 |
| Uvicorn | `==0.54.0` | 精确锁定，ASGI 运行服务器 |
| PyJWT | `==2.15.1` | 精确锁定，HS256 签发与校验 |
| pytest | `>=8.0` | 开发工具，允许小版本升级 |
| ruff | `>=0.6` | 开发工具 |
| httpx | `>=0.27` | 开发工具，FastAPI `TestClient` 依赖 |
| SQLite | Python 内置版本 | 不额外安装 |
| 浏览器 | Chrome / Edge 最新版 | 官方推荐现代浏览器 |

---

## 13. 阶段 5 实现顺序（摘要）

1. `core/`：配置、建表、安全、认证
2. `scripts/init_db.py`：建库 + 管理员
3. `app.py`：路由骨架 + 登录页
4. 学生端：简历 → 职位 → 投递 → 反馈
5. 企业端：资料 → 职位 → 候选人
6. 管理端：企业 / HR / 职位 / 简历审核 + 概览
7. `api/`：`main.py` → `deps.py` → `schemas.py` → 各路由（复用 `services/`）
8. `scripts/export_openapi.py`：导出 `api/openapi.json`
9. 测试补齐与质量门禁
10. README 启动验证

详细验收标准见 [开发路线图](../内部文档/开发路线图.md)。

---

## 14. v1.1 增量设计与实现（2026-11-18）

### 14.1 数据模型增量

`companies` 表新增品牌字段（老库由 `core.db._migrate()` 自动 `ALTER TABLE` 补齐）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `logo_path` | TEXT | logo 相对路径，位于 `uploads/logos/` |
| `intro` | TEXT | 企业简介（≤ 1000 字） |
| `culture` | TEXT | 企业文化（≤ 1000 字） |
| `industry` | TEXT | 所属行业 |
| `company_size` | TEXT | 企业规模 |
| `funding_stage` | TEXT | 融资阶段 |
| `city` | TEXT | 所在城市 |
| `benefits` | TEXT | 福利标签（分隔符分隔） |

新增 `favorites` 表：

```sql
CREATE TABLE favorites (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id     INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    UNIQUE (student_id, job_id)
);
CREATE INDEX idx_favorites_student ON favorites (student_id);
```

### 14.2 服务层增量

| 文件 | 新增 / 变更 |
|---|---|
| `services/jobs.py` | `JOB_SELECT_SQL` 联表品牌字段；`get_public_job`、`search_jobs`（多关键词 / 范围 / 类别 / 排序）、`similar_jobs`、`job_category` |
| `services/recommendations.py` | 新增：简历画像加权评分 + 推荐理由 + 排除已投递 |
| `services/favorites.py` | 新增：收藏切换、收藏 ID 集合、收藏列表 |
| `services/applications.py` | 新增：`batch_apply_to_job`（≤ 20、去重、部分成功）、`applied_job_ids` |
| `services/companies.py` | 新增：`update_branding`、`attach_logo`、`get_company_logo` |
| `core/security.py` | 新增：`validate_image_upload`、`save_image_upload` |
| `core/config.py` | 新增：`LOGO_UPLOAD_DIR`、`MAX_LOGO_MB`、`ALLOWED_IMAGE_EXTENSIONS`、`JOB_CATEGORIES` |

分层约束保持不变：`services/` 与 `core/` 不导入 Streamlit / FastAPI；`views/` 与 `api/` 不直接访问 `sqlite3` 或 `core.db`。

### 14.3 页面层增量

| 文件 | 说明 |
|---|---|
| `views/theme.py` / `views/theme_css.py` | 全局主题、Hero、小节标题、侧边栏品牌 |
| `views/components.py` | 企业品牌面板、logo 占位、标签与职位元信息 |
| `views/student/cards.py` | 职位卡片：收藏、投递、详情、批量选择 |
| `views/student/jobs.py` | 精准搜索、多维筛选、批量投递 |
| `views/student/job_detail.py` | 职位详情（隐藏页面，`visibility="hidden"`） |
| `views/student/recommendations.py` | 智能推荐与推荐画像 |
| `views/student/favorites.py` | 我的收藏 |
| `views/company/profile.py` | 品牌信息维护、logo 上传与预览 |

职位详情通过 `st.query_params["job_id"]` 传参，`st.switch_page` 跳转；导航仍由唯一入口 `app.py` 的 `st.navigation` 统一管理。

### 14.4 REST 接口增量（前缀 `/api/v1`）

| 方法 | 路径 | 角色 | 说明 |
|---|---|---|---|
| GET | `/jobs` | 学生 / 管理员 | 新增 `category`、`search_field`、`sort` 参数 |
| GET | `/jobs/{job_id}` | 学生 / 管理员 | 职位详情（仅 APPROVED） |
| GET | `/jobs/{job_id}/similar` | 学生 / 管理员 | 相似职位 |
| GET | `/jobs/recommendations` | 学生 | 智能推荐 |
| GET | `/jobs/favorites` | 学生 | 我的收藏 |
| POST | `/jobs/{job_id}/favorite` | 学生 | 收藏 / 取消收藏 |
| POST | `/jobs/batch-applications` | 学生 | 批量投递（≤ 20） |
| PUT | `/companies/me/branding` | 企业 | 更新品牌信息 |
| POST | `/companies/me/logo` | 企业 | 上传 logo（multipart） |

API 版本升级为 `1.1.0`，契约文件 [api/openapi.json](../../api/openapi.json) 已重新导出，`tests/test_api_extended.py::test_saved_openapi_matches_live` 校验一致。

### 14.5 搜索与推荐算法

- 关键词：按空白、逗号、顿号、分号、斜杠切分，逐词 `LIKE` 并以 AND 连接；
- 类别：匹配标题中的 `【类别】` 前缀；
- 相似职位：同类目 +5，同城市 +3，标题词重合 +2/词，同企业 +1，仅保留类目或词重合的候选；
- 智能推荐：技能命中 +10/项，专业相关 +6，城市偏好 +3，平台推荐 +2，命中原因随结果返回。

---

## 15. v1.2 增量设计与实现（2026-11-20）

### 15.1 数据模型增量

`jobs` 表新增急招字段（老库由 `_migrate()` 自动补列）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `is_urgent` | INTEGER NOT NULL DEFAULT 0 | 是否急招 |
| `urgent_until` | TEXT | 急招截止日期（ISO `YYYY-MM-DD`） |

新增 5 张表：

| 表 | 关键字段 | 约束 |
|---|---|---|
| `culture_posts` | company_id、user_id、employment_status、is_verified、is_anonymous、topic、title、content、status、official_reply | 任职状态与主题 CHECK、状态 PENDING / APPROVED / REJECTED |
| `company_reviews` | company_id、user_id、employment_status、五维评分、content、status | 评分 1-5 CHECK、`UNIQUE(user_id, company_id, employment_status)` |
| `micro_tasks` | company_id、title、description、city、reward、schedule、headcount、status | 人数 1-100 CHECK、状态 CHECK |
| `task_signups` | task_id、student_id、created_at | `UNIQUE(task_id, student_id)` |
| `job_views` | job_id、student_id、created_at | `UNIQUE(job_id, student_id)`，用于去重浏览 |

同时新增公司索引 `idx_culture_*`、`idx_reviews_*`、`idx_tasks_*`、`idx_job_views_job` 与 `idx_task_signups_task`。

### 15.2 服务层增量

| 文件 | 新增 / 变更 |
|---|---|
| `services/jobs.py` | `JOB_SELECT_SQL` 联查企业口碑评分与样本数；`search_jobs` 增加 `company_id`、`only_urgent`；新增 `set_urgent`、`cancel_urgent` |
| `services/recommendations.py` | 新增企业口碑加权（样本 ≥ 3 且综合分 ≥ 4 时 +3）与推荐理由 |
| `services/culture.py` | 新增：发帖、帖子列表、我的发布、企业回应、管理员审核与频率限制 |
| `services/reviews.py` | 新增：评分提交、样本门槛聚合、企业侧列表、我的评分、管理员审核 |
| `services/micro_tasks.py` | 新增：任务发布、审核、报名、报名名单、结束任务 |
| `services/analytics.py` | 新增：浏览去重记录、企业招聘漏斗与平均响应时长 |
| `services/matching.py` | 新增：候选人匹配打分与可解释理由 |
| `services/content_guard.py` | 新增：内容黑名单校验、简历核验判断 |
| `services/companies.py` | 新增：`list_public_companies`、`get_public_company` |
| `services/admin.py` | 新增：`moderation_counts` 内容审核待办统计 |

所有 UGC 服务遵循：先校验角色 → 校验企业可见性 → 校验内容红线 → 写入待审核状态。

### 15.3 页面层增量

| 文件 | 说明 |
|---|---|
| `views/student/urgent.py` | 急招专区 |
| `views/student/community.py` | 企业文化交流区（浏览 / 发布 / 我的发布） |
| `views/student/company_reviews.py` | 企业评分提交与我的评分 |
| `views/student/micro_tasks.py` | 小任务浏览、报名与我的报名 |
| `views/student/company.py` | 企业主页聚合（隐藏页面） |
| `views/company/dashboard.py` | 招聘效果看板 |
| `views/company/community.py` | 企业官方回应与收到的评分 |
| `views/company/micro_tasks.py` | 小任务发布、报名名单与结束任务 |
| `views/admin/moderation.py` | 文化帖 / 企业评分 / 小任务三合一审核 |

导航仍由 `app.py` 唯一 `st.navigation` 管理；详情页与企业主页使用 `visibility="hidden"`，通过 `st.session_state` + `st.switch_page` 跳转。

### 15.4 REST 接口增量（前缀 `/api/v1`）

| 方法 | 路径 | 角色 | 说明 |
|---|---|---|---|
| GET | `/jobs?only_urgent=true` | 学生 / 管理员 | 急招筛选 |
| GET | `/culture-posts?company_id=` | 学生 / 管理员 | 已通过文化帖 |
| POST | `/culture-posts` | 学生 | 发布经验 / 提问（待审核） |
| GET | `/companies/{id}/reviews` | 学生 / 管理员 | 口碑聚合与评价列表 |
| POST | `/companies/{id}/reviews` | 学生 | 提交评分（待审核） |
| GET | `/micro-tasks` | 学生 / 管理员 | 招募中任务 |
| POST | `/micro-tasks/{id}/signup` | 学生 | 报名任务 |

API 版本升级为 `1.2.0`，契约文件已重新导出；新增错误码 `DUPLICATE_REVIEW`、`DUPLICATE_SIGNUP`、`DUPLICATE_CONTENT`、`TASK_FULL` 映射为 HTTP 409。

### 15.5 评分与匹配算法

- 企业综合口碑：`(成长 + 薪酬 + 面试 + 推荐 + (6 - 强度)) / 5`，仅统计 `APPROVED` 评价；
- 展示门槛：样本 ≥ 3 条才展示数值，避免新企业被 1-2 条极端评分误伤；
- 候选人匹配：技能命中 +10/项、专业 +6、城市偏好 +3，结果附命中理由；
- 招聘看板：浏览去重后计算 `投递转化率 = 投递数 / 浏览数`，平均响应时长按非「已投递」记录计算。

