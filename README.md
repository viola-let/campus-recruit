# 校招平台 CampusRecruit

基于 **Python + Streamlit + FastAPI + SQLite** 的校园招聘与实习选拔平台，面向 Python / Streamlit 初学者，按软件工程规格化流程从零搭建。

平台包含三类角色：**学生端、企业端、平台管理端**，并实现企业资质、企业 HR、职位、简历的**四层独立审核**。

---

## 当前进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| 阶段 0 | 前置准备、目录骨架、工程配置 | ✅ 完成 |
| 阶段 1 | 需求收集与需求搜集清单 | ✅ 完成 |
| 阶段 2 | 功能规格说明书（Spec） | ✅ 完成 |
| 阶段 3 | 技术设计与架构说明书（TDD） | ✅ 完成 |
| 阶段 4 | AI 辅助评审、审查报告 | ✅ 完成 |
| 阶段 5 | AI 生成代码（M0-M6） | ✅ M1-M5 完成；公网部署待执行 |
| 交付物 | 截图、代码打包、公网地址/二维码 | 截图与打包 ✅；公网地址/二维码 ⏳ |

> 三端 UI、四层审核、REST API、146 个自动化测试与模拟测试数据均已就绪，本地 `streamlit run app.py` 与 `uvicorn api.main:app` 已实际跑通。
> v1.1 新增：企业品牌展示、多关键词精准搜索、AI 智能推荐、相似职位、批量投递、岗位收藏与全平台视觉升级。
> v1.2 新增：急招专区、企业文化交流区、企业评分、小任务兼职、招聘看板、候选人匹配排序与企业主页。

---

## 核心功能（v1.2）

| 模块 | 能力 |
|---|---|
| 企业品牌 | 企业可上传 logo、维护简介 / 文化 / 行业 / 规模 / 融资 / 城市 / 福利，展示在岗位列表与详情页 |
| 精准搜索 | 多关键词 AND 搜索（名称 / 描述 / 要求）、仅标题搜索、岗位类别、城市、类型筛选与三种排序 |
| 智能推荐 | 基于简历技能、专业、城市偏好、企业口碑与推荐位加权评分，输出可解释的推荐理由，自动排除已投递职位 |
| 相似职位 | 同类目、同城市、标题关键词重合度综合排序，详情页展示 |
| 批量投递 | 勾选多个职位一键投递，单次最多 20 个，逐条返回成功 / 失败原因 |
| 求职辅助 | 岗位收藏、已投递标记、职位详情页、快捷入口 |
| 急招专区 | 企业设置 1-30 天急招（占比 ≤ 30%），独立入口展示剩余天数，到期自动失效 |
| 企业文化 | 在职 / 曾任职 / 实习过用户分享经验，未任职只能提问；匿名发布、先审后发、企业官方回应 |
| 企业评分 | 五维评分 + 50 字正文，简历核查后可评；样本 < 3 条不展示数值，达标后进入推荐理由 |
| 小任务 | 展会协助等短期任务，关键词拦截刷单 / 押金 / 垫付，先审后发、报名制、平台不碰资金 |
| 企业看板 | 每职位浏览 / 投递 / 面试 / 录用、转化率与平均响应时长 |
| 候选人匹配 | 按技能、专业、城市匹配度排序，展示匹配分与理由，可关闭 |
| 企业主页 | 聚合品牌信息、在招职位、员工分享与员工评分 |
| 视觉升级 | 统一色彩体系、卡片与按钮样式、渐变主视觉、响应式适配移动端 |

完整进入方式（启动步骤、访问地址、账号密码、部署入口、排障）见 [项目进入与访问指引](docs/项目过程文档/11-项目进入与访问指引.md)。

公网免费部署：已提供 `deploy_app.py` 部署入口（自动建库 + 空库导入演示数据），按 [公网免费部署指南](docs/项目过程文档/15-公网免费部署指南.md) 使用 Streamlit Community Cloud 即可获得公开地址。

---

## 内部支撑文档（不纳入最终提交物）

| 文档 | 内容 |
|---|---|
| [前置任务清单](docs/内部文档/前置任务清单.md) | 环境依赖、版本约束、目录标准、编码规范、Git 规则、验收节点 |
| [开发路线图](docs/内部文档/开发路线图.md) | M0-M6 里程碑、每步验收标准与验证命令 |

---

## 最终交付物对照

| # | 交付物 | 文件 / 位置 | 状态 |
|---|---|---|---|
| 1 | 项目介绍文档 | [docs/项目介绍文档.md](docs/项目介绍文档.md) | ✅ 已补全截图 |
| 2 | 项目需求搜集清单 | [docs/项目过程文档/01-项目需求搜集清单.md](docs/项目过程文档/01-项目需求搜集清单.md) | ✅ |
| 3 | 功能规格说明书 | [docs/项目过程文档/02-功能规格说明书.md](docs/项目过程文档/02-功能规格说明书.md) | ✅ |
| 4 | 技术架构说明书（含API设计、数据库设计） | [docs/项目过程文档/03-技术架构说明书（含API设计、数据库设计）.md](docs/项目过程文档/03-技术架构说明书（含API设计、数据库设计）.md) | ✅ |
| 5 | 任务实施计划文档tasks.md | [docs/项目过程文档/04-任务实施计划文档tasks.md](docs/项目过程文档/04-任务实施计划文档tasks.md) | ✅ |
| 6 | 验收清单checklist.md | [docs/项目过程文档/05-验收清单checklist.md](docs/项目过程文档/05-验收清单checklist.md) | ✅ |
| 7 | 审查报告 | [docs/项目过程文档/06-审查报告.md](docs/项目过程文档/06-审查报告.md) | ✅ |
| 8 | 操作手册 | [docs/项目过程文档/07-操作手册.md](docs/项目过程文档/07-操作手册.md) | ✅ |
| 9 | 项目代码打包 | [docs/项目过程文档/08-项目代码打包/项目代码打包.zip](docs/项目过程文档/08-项目代码打包/项目代码打包.zip) | ✅ 已生成并解压验证 |
| 10 | 项目互联网访问地址，或者二维码 | [docs/项目过程文档/09-项目互联网访问地址或二维码.md](docs/项目过程文档/09-项目互联网访问地址或二维码.md) | ⏳ 待公网部署 |
| 11 | 项目进入与访问指引（含本地 / 部署 / 账号） | [docs/项目过程文档/11-项目进入与访问指引.md](docs/项目过程文档/11-项目进入与访问指引.md) | ✅ |
| 12 | v1.2 功能设计方案与实现说明 | [docs/项目过程文档/12-功能设计方案与实现说明.md](docs/项目过程文档/12-功能设计方案与实现说明.md) | ✅ |
| 13 | v1.2 新增功能测试用例说明（前置 / 步骤 / 预期） | [docs/项目过程文档/13-新增功能测试用例说明.md](docs/项目过程文档/13-新增功能测试用例说明.md) | ✅ |
| 14 | 更新日志（v1.0 → v1.2） | [docs/项目过程文档/14-更新日志.md](docs/项目过程文档/14-更新日志.md) | ✅ |
| 15 | 公网免费部署指南（初学者版） | [docs/项目过程文档/15-公网免费部署指南.md](docs/项目过程文档/15-公网免费部署指南.md) | ✅ |
| 补充 | 扩展测试报告与逐条用例 | [测试报告](docs/项目过程文档/10-测试报告.md) · [用例清单](docs/项目过程文档/10-测试用例清单.csv) | ✅ 146 条全部通过 |

---

## 技术基线

| 项 | 版本 / 选择 | 依据 |
|---|---|---|
| Python | 3.12.x（支持 3.11-3.15） | Streamlit 1.67 官方支持范围 |
| Streamlit | 1.67.0（精确锁定） | 2026-11-05 官方最新稳定版 |
| FastAPI | 0.163.2（精确锁定） | REST 适配层，自动生成 OpenAPI 3.1 |
| API 认证 | PyJWT 2.15.1（HS256 Bearer） | 无状态 Token，标准库友好 |
| 数据库 | SQLite（Python 标准库 `sqlite3`） | 零安装、单文件、支持事务 |
| 多页方案 | `st.Page` + `st.navigation` | 官方首选方案 |
| 测试 | pytest + `streamlit.testing.v1.AppTest` | Streamlit 官方测试框架 |
| 代码规范 | PEP 8 + ruff | Python 社区通用标准 |

依赖清单见 [requirements.txt](requirements.txt)、[requirements-dev.txt](requirements-dev.txt)。

---

## 快速开始

> 完整的前置检查见 [前置任务清单](docs/内部文档/前置任务清单.md)。以下命令在项目根目录、PowerShell 中执行。

### 1. 安装 Python 3.12

从 <https://www.python.org/downloads/> 下载安装，务必勾选 **Add python.exe to PATH**。

```powershell
python --version
```

### 2. 创建并激活虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

若提示禁止运行脚本：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```powershell
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 4. 验证环境

```powershell
python -c "import streamlit; print(streamlit.__version__)"
streamlit hello
```

预期输出 `1.67.0`，并自动打开 `http://localhost:8501`。

### 5. 启动本项目

```powershell
python scripts/init_db.py --admin-email admin@example.com --admin-password "ChangeMe123"
python scripts/seed_demo.py
python scripts/seed_test_data.py
streamlit run app.py
```

浏览器打开 `http://localhost:8501`，可使用下方三组演示账号登录。

> `seed_test_data.py` 会写入 20 家公司、50 份简历、30 个岗位与 96 条投递，用于功能演示与测试；重复执行会原子化重置这批模拟数据，不会影响其他账号与数据。详见 [模拟测试数据](#模拟测试数据)。

### 6. 启动 REST 接口（可选）

另开一个终端，仍在项目根目录：

```powershell
.\.venv\Scripts\Activate.ps1
$env:API_JWT_SECRET = "本地开发用的随机长字符串"
uvicorn api.main:app --reload --port 8000
```

页面：`http://localhost:8501`；Swagger：`http://localhost:8000/docs`；契约：`http://localhost:8000/openapi.json`。

> Streamlit 与 FastAPI 是两个独立进程，共用同一份 `data/app.db`。可以只启动其中一个。

### 7. 运行测试

```powershell
pytest -q
```

---

## 演示账号

| 角色 | 邮箱 | 密码 | 说明 |
|---|---|---|---|
| 平台管理员 | `admin@example.com` | `ChangeMe123` | 由初始化脚本创建 |
| 学生 | `student@example.com` | `Student123!` | 演示数据，简历已核查 |
| 企业 | `company@example.com` | `Company123!` | 演示数据，资质与 HR 已通过 |

> 仅用于本地演示，任何真实部署都必须更换密码，并通过环境变量或 `.streamlit/secrets.toml` 提供，不得写入仓库。

### 模拟测试数据

`scripts/seed_test_data.py` 提供一套可重复导入、可随时重置的演示与测试数据：

| 类别 | 规模 | 覆盖范围 |
|---|---|---|
| 企业 | 20 家 | 互联网、金融、制造业、消费品、医疗、能源等 10+ 行业；50-999 人至 10000 人以上；天使轮至已上市；北京、上海、杭州、深圳、广州等城市 |
| 简历 | 50 份 | 应届生 20、初级 10、中级 10、高级 7、技术管理 3；15 所高校；后端/前端/算法/数据/测试/运维/产品/运营/市场/职能 10 个方向 |
| 岗位 | 30 个 | 技术、产品、运营、市场、职能；校招与实习；24 个已通过、3 个待审核、2 个已拒绝、1 个已关闭；5 个推荐位 |
| 投递 | 96 条 | 已投递/已查看/进入面试/已拒绝/已录用五种状态，均由已核查简历投递已通过岗位 |
| 社区 | 3 帖 / 4 评 | 已通过文化帖与企业评分（含 1 条提问），覆盖 3 家企业 |
| 小任务 | 3 个 | 2 个招募中、1 个待审核，含防诈骗提示演示 |
| 浏览 | 12 条 | 用于企业招聘看板的浏览与转化率演示 |

演示账号：

| 角色 | 邮箱 | 密码 |
|---|---|---|
| 学生 | `student01@seed.campus` | `Student123!` |
| 企业 | `company01@seed.campus` | `Company123!` |
| 管理员 | `admin@example.com` | `ChangeMe123` |

重置与安全：

```powershell
python scripts/seed_test_data.py                 # 写入 data/app.db
python scripts/seed_test_data.py --db-path 自定义路径.db
```

- 所有种子账号使用 `@seed.campus` 邮箱域，脚本只清理该域关联的企业、职位、简历、投递与审核日志；
- 若检测到真实学生已投递种子职位，脚本会中止并提示，避免误删正式业务数据；
- 脚本幂等，可反复执行，结果一致；
- 行业、规模、融资阶段、福利、期望薪资、项目经历等扩展属性写入现有文本字段（企业名称、简历摘要、职位描述），不修改表结构。

---

## 目录结构

```text
project2/
├── app.py                  # 唯一入口：全局主题 + 按角色构建导航
├── api/                    # FastAPI REST 适配层：main / deps / schemas / routes
├── core/                   # 配置、数据库、安全、认证
├── services/               # 业务规则（jobs / recommendations / culture / reviews / micro_tasks 等）
├── views/                  # 页面：auth / student / company / admin + theme / components
├── scripts/                # init_db.py、seed_demo.py、seed_test_data.py、export_openapi.py
├── tests/                  # pytest + AppTest
├── data/                   # SQLite 文件（不提交）
├── uploads/                # 简历、营业执照、企业 logo（不提交）
├── docs/
│   ├── 项目介绍文档.md          # 最终提交物（二）
│   ├── 项目过程文档/            # 最终提交物（三）01-14
│   ├── 内部文档/                # 前置清单、开发路线图（不提交）
│   └── images/                  # 截图、访问二维码
├── .streamlit/config.toml  # 官方项目级配置
├── pyproject.toml          # pytest / ruff 配置
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## 四层审核演示路径

```text
1. 企业注册 → 提交营业执照 + HR 资料
2. 管理员审核企业资质（第 1 层）
3. 管理员审核企业 HR（第 2 层）
4. 企业发布职位 → 管理员审核职位（第 3 层）
5. 学生完善简历 → 管理员核查简历（第 4 层）
6. 学生投递 → 企业查看 / 筛选 / 拒绝 / 录用
7. 学生在“我的投递”查看状态与反馈
```

v1.2 社区与急招演示路径：

```text
1. 企业登录 → 职位管理 → 对已通过职位设置急招 7 天
2. 学生登录 → 急招专区 → 查看剩余天数并投递
3. 学生登录 → 企业文化 → 选择企业 → 发布经验（匿名）
4. 管理员登录 → 内容审核 → 通过文化帖
5. 企业登录 → 企业社区 → 对帖子做官方回应
6. 学生登录 → 企业评分 → 五维打分并提交
7. 管理员登录 → 内容审核 → 通过评分
8. 企业登录 → 招聘看板 → 查看浏览、投递与转化率
```

---

## 开发路线图

| 里程碑 | 目标 | 验收节点 |
|---|---|---|
| M0 | 环境就绪 | V0 |
| M1 | 数据与认证：建库、登录、三角色路由 | V1 |
| M2 | 学生端：简历、搜岗、投递、反馈 | V2 |
| M3 | 企业端：资料、职位、候选人 | V3 |
| M4 | 管理端：四层审核、平台概览 | V4 |
| M4.5 | REST API：FastAPI 路由、JWT、OpenAPI 导出 | V4.5 |
| M5 | 质量门禁：测试与端到端验收 | V5 |
| M6 | 交付：README、演示数据、`v1.0.0` | V6 |

详细任务、产出文件与验证命令见 [开发路线图](docs/内部文档/开发路线图.md)。

---

## 质量门禁

```powershell
ruff format --check .
ruff check .
python -m compileall .
pytest -q
```

四项全部通过才允许合并代码。

---

## 已知限制

| 限制 | 说明 |
|---|---|
| SQLite 单文件 | 适合本地演示与课程项目，不适合高并发生产 |
| 本地文件存储 | Streamlit Community Cloud 重启可能丢失 `data/` 与 `uploads/` |
| 会话级认证 | 适合本地；公网应使用 Streamlit 官方 `st.login()` 对接 OIDC |
| REST 仅本地可用 | Community Cloud 只运行一个 Streamlit 进程，公网不提供 REST/OpenAPI |
| 无邮件 / 短信通知 | 学生需主动刷新查看反馈 |
| 无登录限流 | 公网部署前需在网关层补充 |

---

## 官方参考

- [安装 Streamlit](https://docs.streamlit.io/get-started/installation/command-line)
- [st.Page 与 st.navigation](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation)
- [配置项 config.toml](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)
- [应用测试 AppTest](https://docs.streamlit.io/develop/concepts/app-testing)
- [缓存机制](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [客户端-服务端架构](https://docs.streamlit.io/develop/concepts/architecture/architecture)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [OpenAPI 3.1 规范](https://spec.openapis.org/oas/v3.1.0)
