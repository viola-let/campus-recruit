# 任务实施计划（tasks.md）

> 项目：校招平台 CampusRecruit
> 文档版本：v1.1（2026-11-18）
> 对应流程：图 2 阶段 5「AI 生成代码」的实施任务分解
> 上游文档：[Spec](02-功能规格说明书.md)、[TDD](03-技术架构说明书（含API设计、数据库设计）.md)、[开发路线图](../内部文档/开发路线图.md)
> 验收文档：[checklist.md](05-验收清单checklist.md)

---

## 1. 使用说明

1. 任务按里程碑顺序执行，**前置依赖未完成不得开始**。
2. 每个任务完成后，先运行该里程碑的质量门禁，再勾选状态。
3. 任务范围以 Spec 为准，不临时增加功能。
4. 发现需求问题时，先改 Spec/TDD，再改任务，不在代码里“顺手实现”。

### 状态图例

| 标记 | 含义 |
|---|---|
| ✅ | 已完成并通过验收 |
| 🔄 | 进行中 |
| ☐ | 未开始 |
| ⛔ | 阻塞（需记录原因） |

---

## 2. 阶段 0｜文档与工程准备

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-001 | 输出前置任务清单 | `docs/内部文档/前置任务清单.md` | — | 含 P0-P9 与验证命令 | ✅ |
| T-002 | 输出需求搜集清单 | `docs/项目过程文档/01-项目需求搜集清单.md` | — | RQ/DQ 可追溯到 Spec | ✅ |
| T-003 | 输出功能规格说明书 | `docs/项目过程文档/02-功能规格说明书.md` | T-002 | 17 个用户故事与验收标准 | ✅ |
| T-004 | 输出技术架构说明书 | `docs/项目过程文档/03-技术架构说明书（含API设计、数据库设计）.md` | T-003 | 含 API 设计与数据库设计 | ✅ |
| T-005 | 输出审查报告 | `docs/项目过程文档/06-审查报告.md` | T-003、T-004 | P0/P1 问题全部关闭 | ✅ |
| T-006 | 输出开发路线图 | `docs/内部文档/开发路线图.md` | T-004 | M0-M6 均有验收节点 | ✅ |
| T-007 | 输出任务计划 | `docs/项目过程文档/04-任务实施计划文档tasks.md` | T-006 | 本文件 | ✅ |
| T-008 | 输出验收清单 | `docs/项目过程文档/05-验收清单checklist.md` | T-006 | 覆盖文档、功能、安全、交付 | ✅ |
| T-009 | 输出项目介绍文档初稿 | `docs/项目介绍文档.md` | T-003 | 截图清单已预留 | ✅ |
| T-010 | 输出操作手册 | `docs/项目过程文档/07-操作手册.md` | T-004 | 含三端操作与 FAQ | ✅ |
| T-011 | 建立目录骨架与配置文件 | `core/`、`views/`、`services/` 等 | — | 与 TDD 目录一致 | ✅ |

---

## 3. M0｜环境就绪

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-101 | 安装 Python 3.12.x 并加入 PATH | 本机解释器 | — | `python --version` 为 3.12.x | ✅ |
| T-102 | 创建并激活 `.venv` | `.venv/` | T-101 | `sys.prefix` 指向项目 `.venv` | ✅ |
| T-103 | 安装运行时与开发依赖 | `.venv` 中的包 | T-102 | `pip install -r requirements-dev.txt` 成功 | ✅ |
| T-104 | 验证 Streamlit 环境 | — | T-103 | `streamlit hello` 打开 8501 | ✅ |
| T-105 | 初始化 Git 仓库并提交文档 | `.git/`、首个提交 | T-103 | `git status` 干净 | ☐ |

---

## 4. M1｜数据与认证基础

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-201 | 实现配置与枚举 | `core/config.py` | T-105 | 路径、角色、状态、会话 key 齐全 | ✅ |
| T-202 | 实现数据库连接与建表 | `core/db.py` | T-201 | 6 张表、索引、外键开关 | ✅ |
| T-203 | 实现密码哈希与文件校验 | `core/security.py` | T-201 | T-01、T-02、T-10 通过 | ✅ |
| T-204 | 实现注册与登录 | `core/auth.py` | T-202、T-203 | 三角色登录、停用拦截 | ✅ |
| T-205 | 实现初始化脚本 | `scripts/init_db.py` | T-202、T-204 | 可创建管理员 | ✅ |
| T-206 | 实现演示数据脚本 | `scripts/seed_demo.py` | T-205 | 可重复执行不重复建号 | ✅ |
| T-207 | 实现入口与角色路由 | `app.py` | T-204 | 三角色导航隔离、退出清空会话 | ✅ |
| T-208 | 实现登录/注册页面 | `views/auth/login.py` | T-207 | 注册、登录、错误提示 | ✅ |
| T-209 | 编写认证与安全测试 | `tests/test_security.py`、`tests/test_auth.py` | T-208 | T-01 至 T-04 通过 | ✅ |

**里程碑门禁：** `ruff check .`、`compileall`、`pytest tests/test_security.py tests/test_auth.py` 全部通过。

---

## 5. M2｜学生端

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-301 | 实现简历服务 | `services/students.py` | T-202 | 保存后状态为 `PENDING` | ✅ |
| T-302 | 实现职位检索服务 | `services/jobs.py` 的 `search_jobs()` | T-202 | 仅返回 `APPROVED` 职位 | ✅ |
| T-303 | 实现投递服务 | `services/applications.py` 的 `apply_to_job()` | T-301、T-302 | 三条校验 + 快照 | ✅ |
| T-304 | 实现学生首页 | `views/student/home.py` | T-301 | 状态与快捷入口正确 | ✅ |
| T-305 | 实现简历页面 | `views/student/resume.py` | T-301 | 表单、上传、重新送审 | ✅ |
| T-306 | 实现职位广场 | `views/student/jobs.py` | T-302、T-303 | 筛选、空状态、投递 | ✅ |
| T-307 | 实现我的投递 | `views/student/applications.py` | T-303 | 状态、反馈、时间倒序 | ✅ |
| T-308 | 编写投递规则测试 | `tests/test_services.py` | T-303 | T-05、T-06 通过 | ✅ |

**里程碑门禁：** 学生主流程手工走查通过，T-05、T-06 通过。

---

## 6. M3｜企业端

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-401 | 实现企业资料服务 | `services/companies.py` | T-202 | 双审核状态、资料回 `PENDING` | ✅ |
| T-402 | 实现职位管理服务 | `services/jobs.py` 的创建/编辑/关闭/重开 | T-401 | 双审通过才可发布 | ✅ |
| T-403 | 实现候选人服务 | `services/applications.py` 的查询与状态流转 | T-402 | 归属校验、允许流转 | ✅ |
| T-404 | 实现企业首页 | `views/company/home.py` | T-401 | 审核状态与待办正确 | ✅ |
| T-405 | 实现企业资料页 | `views/company/profile.py` | T-401 | 上传与状态展示 | ✅ |
| T-406 | 实现职位管理页 | `views/company/jobs.py` | T-402 | 发布、编辑、关闭、重提 | ✅ |
| T-407 | 实现候选人页 | `views/company/candidates.py` | T-403 | 筛选、查看快照、下载、反馈 | ✅ |
| T-408 | 编写企业越权与状态测试 | `tests/test_services.py` | T-403 | T-07、T-08 通过 | ✅ |

**里程碑门禁：** 企业主流程手工走查通过，T-07、T-08 通过。

---

## 7. M4｜管理端

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-501 | 实现企业与 HR 审核服务 | `services/companies.py` | T-401 | 双状态独立审核、写日志 | ✅ |
| T-502 | 实现职位审核与推荐 | `services/jobs.py` | T-402 | `PENDING` 才可审、仅通过可推荐 | ✅ |
| T-503 | 实现简历核查 | `services/students.py` | T-301 | `PENDING` 才可审、理由必填 | ✅ |
| T-504 | 实现统计与待办 | `services/admin.py` | T-501 至 T-503 | 6 项指标与队列一致 | ✅ |
| T-505 | 实现管理端概览 | `views/admin/home.py` | T-504 | 指标可跳转 | ✅ |
| T-506 | 实现企业审核页 | `views/admin/companies.py` | T-501 | 资质 / HR 两页签 | ✅ |
| T-507 | 实现职位审核页 | `views/admin/jobs.py` | T-502 | 通过、拒绝、推荐 | ✅ |
| T-508 | 实现简历核查页 | `views/admin/resumes.py` | T-503 | 通过、拒绝、理由 | ✅ |
| T-509 | 编写审核权限与并发测试 | `tests/test_services.py` | T-501 至 T-503 | T-09 通过 | ✅ |

**里程碑门禁：** 四层审核端到端走查通过，T-09 通过。

---

## 7.5 M4.5｜REST API 适配层

> 来源：D-01「FastAPI 运行级 REST」决策。REST 层只做协议适配，业务规则全部复用 `services/`，不得复制逻辑。

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-510 | 搭建 FastAPI 应用骨架 | `api/main.py` | T-204 | `/health` 返回 200；CORS 仅允许 `localhost:8501` | ✅ |
| T-511 | 实现 JWT 签发与鉴权依赖 | `api/deps.py`、`core/security.py` | T-204 | 无 Token 返回 401；角色不符返回 403 | ✅ |
| T-512 | 实现认证路由与请求/响应模型 | `api/routes/auth.py`、`api/schemas.py` | T-510、T-511 | 注册 / 登录 / `/auth/me` 与 UI 行为一致 | ✅ |
| T-513 | 实现学生、企业、职位与投递路由 | `api/routes/students.py`、`companies.py`、`jobs.py`、`applications.py` | T-512 | 全部调用 `services/`，无 SQL | ✅ |
| T-514 | 实现管理端路由 | `api/routes/admin.py` | T-513 | 四层审核接口可调用 | ✅ |
| T-515 | 导出 OpenAPI 并编写接口测试 | `api/openapi.json`、`tests/test_api.py`、`scripts/export_openapi.py` | T-514 | `openapi.json` 生成；TestClient 用例通过 | ✅ |

**里程碑门禁：** `uvicorn api.main:app` 可启动；`/docs` 可打开；`api/openapi.json` 已导出；接口测试通过。

---

## 8. M5｜质量门禁

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-601 | 完善测试夹具 | `tests/conftest.py` | T-509 | 临时库、临时上传目录 | ✅ |
| T-602 | 补齐安全测试 | `tests/test_security.py` | T-203 | T-01、T-02、T-10 | ✅ |
| T-603 | 补齐认证测试 | `tests/test_auth.py` | T-204 | T-03、T-04、角色路由 | ✅ |
| T-604 | 补齐服务测试 | `tests/test_services.py` | T-509 | T-05 至 T-09 | ✅ |
| T-605 | 编写 AppTest 冒烟测试 | `tests/test_app_smoke.py` | T-508 | T-11、T-12 | ✅ |
| T-606 | 执行四项质量门禁 | 检查记录 | T-601 至 T-605 | 全部通过 | ✅ |
| T-607 | 三端主流程人工走查 | 走查记录 | T-606 | 无阻塞 | ✅ |

**里程碑门禁：**

```powershell
ruff format --check .
ruff check .
python -m compileall .
pytest -q
```

---

## 9. M6｜交付与部署

| ID | 任务 | 产出 | 依赖 | 验收 | 状态 |
|---|---|---|---|---|---|
| T-701 | 更新 README 为最终版 | `README.md` | T-606 | 5 条命令可启动 | ✅ |
| T-702 | 采集关键页面截图 | `docs/images/*.png` | T-607 | 6 张截图与界面一致 | ✅ |
| T-703 | 补全项目介绍文档 | `docs/项目介绍文档.md` | T-702 | 截图与功能介绍完整 | ✅ |
| T-704 | 核对依赖锁文件 | `requirements.txt` | T-606 | 与 `pip freeze` 一致 | ✅ |
| T-705 | 打包项目代码 | `docs/项目过程文档/08-项目代码打包/项目代码打包.zip` | T-701、T-704 | 解压可启动，无敏感文件 | ✅ |
| T-706 | 部署公网演示 | 可访问 URL | T-705 | 三端可登录 | ☐ |
| T-707 | 生成访问二维码 | `docs/images/access-qr.png` | T-706 | 扫码打开同一地址 | ☐ |
| T-708 | 更新 checklist 并打标签 | `docs/项目过程文档/05-验收清单checklist.md`、`v1.0.0` | T-701 至 T-707 | 全部验收项通过 | ☐ |

---

## 10. 任务依赖关系（关键路径）

```text
T-101 → T-102 → T-103 → T-105
                          │
T-201 → T-202 → T-203 → T-204 → T-205 → T-206
                          │
T-207 → T-208 → T-209
                          │
T-301 → T-303 → T-306 → T-308
                          │
T-401 → T-402 → T-403 → T-407 → T-408
                          │
T-501 → T-502 → T-503 → T-504 → T-509
                          │
T-510 → T-511 → T-512 → T-513 → T-514 → T-515
                          │
T-601 → T-606 → T-607 → T-701 → T-702 → T-705 → T-706 → T-707 → T-708
```

> 关键路径上的任何任务延期，都会直接影响最终交付；非关键任务（如项目介绍初稿）可并行。

---

## 11. 变更规则

1. 新增任务必须写明来源需求 ID（`RQ-*` 或 `US-*`）。
2. 删除任务必须说明原因，并同步更新 `checklist.md`。
3. 任务状态只在通过对应验收后修改。
4. 任何任务都不得绕过质量门禁。

---

## 12. 当前进度摘要

| 阶段 | 任务数 | 已完成 | 进行中 | 未开始 |
|---|---|---|---|---|
| 阶段 0 文档与工程准备 | 11 | 11 | 0 | 0 |
| M0 环境就绪 | 5 | 4 | 0 | 1 |
| M1 数据与认证 | 9 | 9 | 0 | 0 |
| M2 学生端 | 8 | 8 | 0 | 0 |
| M3 企业端 | 8 | 8 | 0 | 0 |
| M4 管理端 | 9 | 9 | 0 | 0 |
| M4.5 REST API 适配层 | 6 | 6 | 0 | 0 |
| M5 质量门禁 | 7 | 7 | 0 | 0 |
| M6 交付与部署 | 8 | 5 | 0 | 3 |
| **合计** | **71** | **67** | **0** | **4** |

> 未完成项：T-105 与 T-708 需要 Git 提交/打标签（需项目负责人确认）；T-706 公网部署与 T-707 二维码需要可用的托管账号。代码、测试与本地三端已全部跑通。

---

## v1.1 增量任务（2026-11-18）

| 编号 | 任务 | 产出 | 状态 |
|---|---|---|---|
| T-901 | 企业品牌数据模型与迁移 | `core/db.py`、`core/config.py` | ✅ |
| T-902 | 品牌服务与 logo 上传 | `services/companies.py`、`core/security.py` | ✅ |
| T-903 | 品牌信息维护与预览页面 | `views/company/profile.py` | ✅ |
| T-904 | 岗位联合品牌字段展示 | `services/jobs.py`、`views/components.py` | ✅ |
| T-905 | 多关键词精准搜索与筛选排序 | `services/jobs.py`、`views/student/jobs.py` | ✅ |
| T-906 | 职位详情页与相似职位 | `views/student/job_detail.py`、`jobs.similar_jobs` | ✅ |
| T-907 | 智能推荐服务与页面 | `services/recommendations.py`、`views/student/recommendations.py` | ✅ |
| T-908 | 批量投递 | `services/applications.py`、`views/student/jobs.py` | ✅ |
| T-909 | 岗位收藏与我的收藏 | `services/favorites.py`、`views/student/favorites.py` | ✅ |
| T-910 | 全平台主题与响应式改造 | `views/theme.py`、`views/theme_css.py`、`views/components.py` | ✅ |
| T-911 | REST 接口扩展与契约导出 | `api/routes/*`、`api/openapi.json` | ✅ |
| T-912 | 种子数据补充品牌与收藏 | `scripts/seed_test_data.py` | ✅ |
| T-913 | 新增功能测试与回归 | `tests/test_new_features.py` | ✅ 8 条新增，121 条全部通过 |
| T-914 | 文档同步 | README、02/03/04/05/07/08/10/11 | ✅ |

> v1.1 全部任务已完成，无遗留开发项；部署类事项仍与 v1.0 一致。

---

## v1.2 增量任务（2026-11-20）

| 编号 | 任务 | 产出 | 状态 |
|---|---|---|---|
| T-1001 | 急招字段与迁移 | `core/db.py`、`core/config.py` | ✅ |
| T-1002 | 急招设置 / 取消与比例上限 | `services/jobs.py` | ✅ |
| T-1003 | 急招专区页面与卡片标签 | `views/student/urgent.py`、`views/student/cards.py` | ✅ |
| T-1004 | 文化社区数据模型与服务 | `core/db.py`、`services/culture.py`、`services/content_guard.py` | ✅ |
| T-1005 | 文化社区学生端页面 | `views/student/community.py` | ✅ |
| T-1006 | 企业评分服务与页面 | `services/reviews.py`、`views/student/company_reviews.py` | ✅ |
| T-1007 | 评分接入推荐算法 | `services/recommendations.py` | ✅ |
| T-1008 | 小任务数据模型与服务 | `core/db.py`、`services/micro_tasks.py` | ✅ |
| T-1009 | 小任务学生端与企业端页面 | `views/student/micro_tasks.py`、`views/company/micro_tasks.py` | ✅ |
| T-1010 | 企业招聘效果看板 | `services/analytics.py`、`views/company/dashboard.py` | ✅ |
| T-1011 | 候选人智能匹配排序 | `services/matching.py`、`views/company/candidates.py` | ✅ |
| T-1012 | 企业主页聚合与详情联动 | `views/student/company.py`、`views/student/job_detail.py` | ✅ |
| T-1013 | 企业官方回应与评分查看 | `views/company/community.py` | ✅ |
| T-1014 | 管理端内容审核队列 | `views/admin/moderation.py`、`views/admin/home.py`、`services/admin.py` | ✅ |
| T-1015 | REST 接口与契约扩展 | `api/routes/community.py`、`api/schemas.py`、`api/openapi.json` | ✅ |
| T-1016 | 种子数据补充社区 / 任务 / 浏览 | `scripts/seed_test_data.py` | ✅ |
| T-1017 | 新增功能测试与全量回归 | `tests/test_v12_features.py`、`tests/test_v12_case_matrix.py` | ✅ 25 条新增，146 条全部通过 |
| T-1018 | 文档同步 | README、02/03/04/05/07/10/11/12/13/14 | ✅ |
| T-1019 | 功能展示素材与演示面板 | 服务注释、页面「功能说明与演示要点」、演示脚本 | ✅ |

> v1.2 已完成三项需求与 E1/E2/E5 企业端能力；E3 人才库、E4 面试邀约、E6 反馈模板列入 P2 规划。

