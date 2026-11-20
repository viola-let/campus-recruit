"""导入用于测试与演示的模拟数据：20 家公司、50 份简历、30 个岗位。

特点：
- 只操作邮箱域名为 ``@seed.campus`` 的种子账号，重复执行会先清理再重建；
- 不会删除 ``@example.com`` 等真实/原有账号；
- 所有数据由固定规则生成，结果稳定可复现；
- 通过 ``--db-path`` 可以写入独立数据库，避免影响正式数据。

用法：
    python scripts/seed_test_data.py
    python scripts/seed_test_data.py --db-path data/demo_seed.db

演示账号（全部种子账号共用密码）：
    学生  student01@seed.campus / Student123!
    企业  company01@seed.campus / Company123!

说明：现有数据模型没有“行业 / 融资阶段 / 福利标签 / 期望薪资”等独立字段，
因此这些信息被写入企业名称、简历 summary 与职位 description，便于演示与搜索，
但不支持按这些维度做结构化筛选。如需结构化筛选，应先扩展表结构。
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import CN_TZ, Role  # noqa: E402
from core.db import get_connection, init_db, query_one  # noqa: E402
from core.security import hash_password  # noqa: E402

SEED_DOMAIN = "@seed.campus"
STUDENT_PASSWORD = "Student123!"
COMPANY_PASSWORD = "Company123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "ChangeMe123"

CITIES = [
    "北京",
    "上海",
    "深圳",
    "杭州",
    "广州",
    "成都",
    "南京",
    "武汉",
    "苏州",
    "西安",
    "无锡",
    "重庆",
    "常州",
]

COMPANY_SEEDS = [
    {
        "name": "云启科技",
        "industry": "互联网",
        "size": "500-999人",
        "funding": "C轮",
        "city": "杭州",
        "benefits": "六险一金、弹性工作、年度体检、技术分享",
        "hr": "陈招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "星链数据",
        "industry": "人工智能",
        "size": "100-499人",
        "funding": "B轮",
        "city": "北京",
        "benefits": "六险一金、股票期权、免费三餐、GPU 集群",
        "hr": "李招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "恒信金融",
        "industry": "金融",
        "size": "1000-4999人",
        "funding": "已上市",
        "city": "上海",
        "benefits": "五险一金、补充医疗、年终奖、带薪年假",
        "hr": "周招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "智造精密",
        "industry": "制造业",
        "size": "1000-4999人",
        "funding": "战略融资",
        "city": "苏州",
        "benefits": "五险一金、班车、餐补、技能培训",
        "hr": "吴招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "悦享消费",
        "industry": "消费品",
        "size": "500-999人",
        "funding": "D轮",
        "city": "广州",
        "benefits": "六险一金、内购折扣、节日礼品、弹性打卡",
        "hr": "郑招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "康泽医疗",
        "industry": "医疗健康",
        "size": "100-499人",
        "funding": "A轮",
        "city": "成都",
        "benefits": "五险一金、补充医疗、年度体检、双休",
        "hr": "王招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "启明教育",
        "industry": "教育",
        "size": "100-499人",
        "funding": "B轮",
        "city": "武汉",
        "benefits": "五险一金、寒暑假、培训基金、下午茶",
        "hr": "冯招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "绿驰新能源",
        "industry": "新能源",
        "size": "1000-4999人",
        "funding": "C轮",
        "city": "常州",
        "benefits": "五险一金、住宿补贴、班车、年终奖",
        "hr": "蒋招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "顺达物流",
        "industry": "物流",
        "size": "5000人以上",
        "funding": "已上市",
        "city": "深圳",
        "benefits": "五险一金、餐补、交通补贴、带薪年假",
        "hr": "韩招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "幻境游戏",
        "industry": "游戏",
        "size": "100-499人",
        "funding": "B轮",
        "city": "上海",
        "benefits": "六险一金、项目奖金、游戏基金、弹性工作",
        "hr": "曹招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "云帆企服",
        "industry": "企业服务",
        "size": "100-499人",
        "funding": "C轮",
        "city": "北京",
        "benefits": "六险一金、股票期权、远程办公、年度旅游",
        "hr": "沈招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "芯航半导体",
        "industry": "半导体",
        "size": "1000-4999人",
        "funding": "D轮",
        "city": "无锡",
        "benefits": "五险一金、住房补贴、股票期权、班车",
        "hr": "许招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "远驰汽车",
        "industry": "汽车",
        "size": "5000人以上",
        "funding": "已上市",
        "city": "重庆",
        "benefits": "五险一金、购车优惠、年终奖、补充医疗",
        "hr": "何招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "优选电商",
        "industry": "电商",
        "size": "1000-4999人",
        "funding": "已上市",
        "city": "杭州",
        "benefits": "六险一金、内购折扣、餐补、弹性工作",
        "hr": "吕招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "深瞳智能",
        "industry": "人工智能",
        "size": "100-499人",
        "funding": "C轮",
        "city": "深圳",
        "benefits": "六险一金、股票期权、免费三餐、健身补贴",
        "hr": "施招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "万象传媒",
        "industry": "文化传媒",
        "size": "100-499人",
        "funding": "A轮",
        "city": "上海",
        "benefits": "五险一金、项目奖金、弹性工作、下午茶",
        "hr": "张招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "安居地产",
        "industry": "房地产",
        "size": "5000人以上",
        "funding": "已上市",
        "city": "广州",
        "benefits": "五险一金、补充医疗、带薪年假、节日福利",
        "hr": "孔招聘",
        "status": "APPROVED",
        "hr_status": "APPROVED",
        "note": None,
    },
    {
        "name": "沃野农业",
        "industry": "农业科技",
        "size": "100-499人",
        "funding": "A轮",
        "city": "西安",
        "benefits": "五险一金、包吃住、交通补贴、年终奖",
        "hr": "崔招聘",
        "status": "PENDING",
        "hr_status": "PENDING",
        "note": None,
    },
    {
        "name": "生元生物",
        "industry": "生物科技",
        "size": "100-499人",
        "funding": "B轮",
        "city": "苏州",
        "benefits": "五险一金、补充医疗、年度体检、双休",
        "hr": "严招聘",
        "status": "APPROVED",
        "hr_status": "PENDING",
        "note": None,
    },
    {
        "name": "迅联通信",
        "industry": "通信",
        "size": "1000-4999人",
        "funding": "已上市",
        "city": "南京",
        "benefits": "五险一金、通讯补贴、年终奖、班车",
        "hr": "金招聘",
        "status": "REJECTED",
        "hr_status": "PENDING",
        "note": "营业执照影像不清晰，请重新上传后提交",
    },
]

JOB_SEEDS = [
    {
        "company": 1,
        "title": "Python 后端工程师",
        "category": "技术",
        "track": "后端",
        "type": "CAMPUS",
        "salary": "18-30K",
        "need": "负责校招平台核心接口开发、性能优化与线上问题排查。",
        "req": "熟悉 Python、FastAPI 与 MySQL，理解常见缓存与消息队列。",
        "status": "APPROVED",
        "featured": True,
    },
    {
        "company": 1,
        "title": "前端开发工程师",
        "category": "技术",
        "track": "前端",
        "type": "CAMPUS",
        "salary": "15-25K",
        "need": "负责招聘平台 Web 端与运营后台的页面开发与体验优化。",
        "req": "掌握 JavaScript、TypeScript 与 React，了解工程化构建。",
        "status": "APPROVED",
    },
    {
        "company": 2,
        "title": "机器学习算法工程师",
        "category": "技术",
        "track": "算法",
        "type": "CAMPUS",
        "salary": "25-40K",
        "need": "负责推荐与搜索排序模型的设计、训练与线上效果迭代。",
        "req": "熟悉 PyTorch、推荐系统与特征工程，有竞赛或论文经历优先。",
        "status": "APPROVED",
        "featured": True,
    },
    {
        "company": 2,
        "title": "数据开发实习生",
        "category": "技术",
        "track": "数据",
        "type": "INTERN",
        "salary": "200-350 元/天",
        "need": "参与离线数仓建设、指标开发与数据质量监控。",
        "req": "掌握 SQL 与 Python，了解 Hive、Spark 等大数据组件。",
        "status": "APPROVED",
    },
    {
        "company": 3,
        "title": "Java 后端工程师（风控方向）",
        "category": "技术",
        "track": "后端",
        "type": "CAMPUS",
        "salary": "20-35K",
        "need": "负责风控规则引擎与授信系统的后端开发与稳定性保障。",
        "req": "熟悉 Java、Spring Boot 与 MySQL，了解高并发场景。",
        "status": "APPROVED",
    },
    {
        "company": 4,
        "title": "工业软件后端工程师",
        "category": "技术",
        "track": "后端",
        "type": "CAMPUS",
        "salary": "15-25K",
        "need": "负责工业设备管理平台的后端服务与数据采集接口开发。",
        "req": "熟悉 Python 或 Java，了解 MES、物联网协议者优先。",
        "status": "APPROVED",
    },
    {
        "company": 4,
        "title": "自动化测试实习生",
        "category": "技术",
        "track": "测试",
        "type": "INTERN",
        "salary": "180-300 元/天",
        "need": "参与设备管理平台的接口自动化与回归测试建设。",
        "req": "了解 Pytest 或 Selenium，具备基础的 Linux 操作能力。",
        "status": "APPROVED",
    },
    {
        "company": 8,
        "title": "电池系统测试工程师",
        "category": "技术",
        "track": "测试",
        "type": "CAMPUS",
        "salary": "15-25K",
        "need": "负责电池管理系统测试方案设计、执行与问题跟踪。",
        "req": "了解 CAN 总线与测试流程，具备数据分析基础。",
        "status": "APPROVED",
    },
    {
        "company": 9,
        "title": "Go 后端工程师",
        "category": "技术",
        "track": "后端",
        "type": "CAMPUS",
        "salary": "20-32K",
        "need": "负责物流调度与轨迹服务的高性能后端开发。",
        "req": "熟悉 Go 与 MySQL，理解分布式系统与常见中间件。",
        "status": "APPROVED",
    },
    {
        "company": 10,
        "title": "Unity 客户端工程师",
        "category": "技术",
        "track": "前端",
        "type": "CAMPUS",
        "salary": "18-30K",
        "need": "负责休闲游戏客户端玩法开发、性能优化与版本维护。",
        "req": "熟悉 Unity 与 C#，有完整游戏项目经历优先。",
        "status": "APPROVED",
    },
    {
        "company": 12,
        "title": "Linux 运维工程师",
        "category": "技术",
        "track": "运维",
        "type": "CAMPUS",
        "salary": "15-24K",
        "need": "负责研发环境与生产集群的部署、监控和故障处理。",
        "req": "熟悉 Linux、Docker 与 Shell，了解 Kubernetes 基础。",
        "status": "APPROVED",
    },
    {
        "company": 15,
        "title": "计算机视觉算法实习生",
        "category": "技术",
        "track": "算法",
        "type": "INTERN",
        "salary": "250-400 元/天",
        "need": "参与目标检测与图像分割模型的训练和部署。",
        "req": "熟悉 PyTorch 与常见视觉模型，能阅读英文论文。",
        "status": "PENDING",
    },
    {
        "company": 1,
        "title": "产品经理",
        "category": "产品",
        "track": "产品",
        "type": "CAMPUS",
        "salary": "15-25K",
        "need": "负责招聘业务需求分析、原型设计与版本节奏推进。",
        "req": "具备需求拆解与数据分析能力，有校园项目经历优先。",
        "status": "APPROVED",
        "featured": True,
    },
    {
        "company": 6,
        "title": "医疗产品经理",
        "category": "产品",
        "track": "产品",
        "type": "CAMPUS",
        "salary": "15-25K",
        "need": "负责互联网医疗产品的需求调研、方案设计与落地。",
        "req": "了解医疗行业者优先，具备良好的沟通与文档能力。",
        "status": "PENDING",
    },
    {
        "company": 11,
        "title": "B 端产品经理",
        "category": "产品",
        "track": "产品",
        "type": "CAMPUS",
        "salary": "18-28K",
        "need": "负责企业协同产品的功能规划、客户调研与迭代管理。",
        "req": "具备 B 端产品思维，熟悉原型工具与需求管理流程。",
        "status": "APPROVED",
    },
    {
        "company": 14,
        "title": "电商产品经理",
        "category": "产品",
        "track": "产品",
        "type": "CAMPUS",
        "salary": "18-30K",
        "need": "负责交易链路与营销工具的产品设计与效果复盘。",
        "req": "熟悉电商业务，具备数据驱动与跨团队协作能力。",
        "status": "APPROVED",
    },
    {
        "company": 5,
        "title": "电商运营",
        "category": "运营",
        "track": "运营",
        "type": "CAMPUS",
        "salary": "12-20K",
        "need": "负责店铺日常运营、商品上新与销售数据分析。",
        "req": "熟悉主流电商平台规则，具备活动策划与执行能力。",
        "status": "APPROVED",
        "featured": True,
    },
    {
        "company": 7,
        "title": "用户运营实习生",
        "category": "运营",
        "track": "运营",
        "type": "INTERN",
        "salary": "180-300 元/天",
        "need": "参与用户分层、社群维护与学习活动运营。",
        "req": "沟通表达良好，熟悉 Excel 与常见社群工具。",
        "status": "CLOSED",
    },
    {
        "company": 14,
        "title": "活动运营",
        "category": "运营",
        "track": "运营",
        "type": "CAMPUS",
        "salary": "12-20K",
        "need": "负责平台大促活动的方案策划、资源协调与复盘。",
        "req": "具备活动执行经验，能在快节奏环境下推进项目。",
        "status": "APPROVED",
    },
    {
        "company": 16,
        "title": "内容运营",
        "category": "运营",
        "track": "运营",
        "type": "CAMPUS",
        "salary": "12-18K",
        "need": "负责新媒体内容的选题、生产与数据效果跟踪。",
        "req": "文字功底扎实，熟悉短视频与社交平台内容生态。",
        "status": "APPROVED",
    },
    {
        "company": 9,
        "title": "供应链运营",
        "category": "运营",
        "track": "运营",
        "type": "CAMPUS",
        "salary": "12-20K",
        "need": "负责运输资源协调、时效监控与异常订单处理。",
        "req": "熟悉 Excel 与数据分析，具备较强的协调推动能力。",
        "status": "APPROVED",
    },
    {
        "company": 5,
        "title": "品牌市场专员",
        "category": "市场",
        "track": "市场",
        "type": "CAMPUS",
        "salary": "12-20K",
        "need": "负责品牌传播方案、内容投放与市场活动执行。",
        "req": "具备文案与活动策划能力，关注消费行业趋势。",
        "status": "APPROVED",
        "featured": True,
    },
    {
        "company": 16,
        "title": "市场推广",
        "category": "市场",
        "track": "市场",
        "type": "CAMPUS",
        "salary": "12-18K",
        "need": "负责渠道投放、异业合作与市场数据复盘。",
        "req": "熟悉主流投放平台，具备数据敏感度与执行力。",
        "status": "REJECTED",
        "note": "薪资范围与岗位职责不匹配，请调整后重新提交",
    },
    {
        "company": 17,
        "title": "市场策划",
        "category": "市场",
        "track": "市场",
        "type": "CAMPUS",
        "salary": "12-20K",
        "need": "负责楼盘营销活动策划、物料统筹与效果评估。",
        "req": "具备活动策划经验，沟通协调能力强。",
        "status": "APPROVED",
    },
    {
        "company": 14,
        "title": "渠道市场",
        "category": "市场",
        "track": "市场",
        "type": "CAMPUS",
        "salary": "12-20K",
        "need": "负责渠道伙伴拓展、联合营销与销售线索转化。",
        "req": "具备商务沟通能力，能适应短期出差。",
        "status": "APPROVED",
    },
    {
        "company": 3,
        "title": "财务分析",
        "category": "职能",
        "track": "职能",
        "type": "CAMPUS",
        "salary": "15-25K",
        "need": "负责经营数据分析、预算编制与成本优化建议。",
        "req": "熟悉财务分析与 Excel，具备良好的数据敏感度。",
        "status": "APPROVED",
    },
    {
        "company": 17,
        "title": "HR 招聘专员",
        "category": "职能",
        "track": "职能",
        "type": "CAMPUS",
        "salary": "10-18K",
        "need": "负责校园招聘、面试安排与人才库维护。",
        "req": "沟通表达良好，熟悉招聘流程与常见面试方法。",
        "status": "APPROVED",
    },
    {
        "company": 6,
        "title": "行政专员",
        "category": "职能",
        "track": "职能",
        "type": "CAMPUS",
        "salary": "8-14K",
        "need": "负责办公用品、会议安排与日常行政事务管理。",
        "req": "细致耐心，熟练使用 Office 办公软件。",
        "status": "PENDING",
    },
    {
        "company": 11,
        "title": "法务助理",
        "category": "职能",
        "track": "职能",
        "type": "CAMPUS",
        "salary": "12-20K",
        "need": "负责合同审核、法律检索与合规材料整理。",
        "req": "法学相关专业，通过法律职业资格考试者优先。",
        "status": "APPROVED",
    },
    {
        "company": 13,
        "title": "采购专员",
        "category": "职能",
        "track": "职能",
        "type": "CAMPUS",
        "salary": "10-16K",
        "need": "负责零部件采购、供应商管理与交期跟踪。",
        "req": "具备谈判与数据分析能力，了解汽车供应链者优先。",
        "status": "REJECTED",
        "note": "岗位职责描述过于笼统，请补充具体采购品类",
    },
]

NAMES = [
    "张伟",
    "王芳",
    "李娜",
    "刘洋",
    "陈晨",
    "杨帆",
    "黄磊",
    "赵静",
    "周涛",
    "吴敏",
    "徐强",
    "孙悦",
    "马超",
    "朱婷",
    "胡军",
    "郭鹏",
    "林晓",
    "何欣",
    "高翔",
    "罗丹",
    "郑凯",
    "梁爽",
    "谢婷",
    "唐磊",
    "韩雪",
    "曹阳",
    "邓超",
    "冯媛",
    "曾辉",
    "程琳",
    "彭博",
    "潘婷",
    "袁华",
    "于倩",
    "董磊",
    "余静",
    "苏航",
    "叶青",
    "吕明",
    "魏然",
    "蒋雯",
    "杜鹏",
    "丁宁",
    "任杰",
    "沈璐",
    "姚远",
    "卢俊",
    "姜楠",
    "崔浩",
    "钟慧",
]

SCHOOLS = [
    "浙江大学",
    "上海交通大学",
    "复旦大学",
    "北京邮电大学",
    "华中科技大学",
    "南京大学",
    "武汉大学",
    "中山大学",
    "四川大学",
    "西安电子科技大学",
    "苏州大学",
    "深圳大学",
    "杭州电子科技大学",
    "重庆大学",
    "江南大学",
]

TRACKS = [
    "后端",
    "前端",
    "算法",
    "数据",
    "测试",
    "运维",
    "产品",
    "运营",
    "市场",
    "职能",
]

TRACK_MAJORS = {
    "后端": ["计算机科学与技术", "软件工程", "网络工程"],
    "前端": ["软件工程", "计算机科学与技术", "数字媒体技术"],
    "算法": ["人工智能", "计算机科学与技术", "自动化"],
    "数据": ["数据科学与大数据技术", "统计学", "计算机科学与技术"],
    "测试": ["软件工程", "计算机科学与技术", "电子信息工程"],
    "运维": ["计算机科学与技术", "网络工程", "信息安全"],
    "产品": ["信息管理与信息系统", "工商管理", "计算机科学与技术"],
    "运营": ["电子商务", "市场营销", "新闻传播学"],
    "市场": ["市场营销", "广告学", "工商管理"],
    "职能": ["人力资源管理", "财务管理", "工商管理"],
}

TRACK_SKILLS = {
    "后端": ["Python", "FastAPI", "MySQL", "Redis", "Docker"],
    "前端": ["JavaScript", "TypeScript", "React", "Vue", "Webpack"],
    "算法": ["Python", "PyTorch", "机器学习", "NLP", "模型调优"],
    "数据": ["SQL", "Python", "Spark", "Hive", "数据建模"],
    "测试": ["Pytest", "接口测试", "Selenium", "性能测试", "Jenkins"],
    "运维": ["Linux", "Docker", "Kubernetes", "Shell", "监控告警"],
    "产品": ["需求分析", "原型设计", "Axure", "数据分析", "项目管理"],
    "运营": ["用户运营", "活动策划", "数据分析", "内容运营", "增长实验"],
    "市场": ["品牌策划", "市场调研", "渠道拓展", "文案写作", "数据分析"],
    "职能": ["招聘管理", "薪酬核算", "Excel", "劳动法", "沟通协调"],
}

TRACK_PROJECTS = {
    "后端": [
        "校招平台订单服务：使用 FastAPI + MySQL 实现投递与状态流转，"
        "接口 P95 延迟降至 {metric}ms。",
        "内部权限系统重构：引入 Redis 缓存与 RBAC 模型，接口吞吐提升 {metric}%。",
    ],
    "前端": [
        "招聘后台重构：使用 React + TypeScript 拆分组件，首屏加载时间缩短 {metric}%。",
        "运营活动页搭建：沉淀可复用组件与埋点方案，活动上线效率提升 {metric}%。",
    ],
    "算法": [
        "推荐排序模型优化：引入特征交叉与重排策略，线上点击率提升 {metric}%。",
        "文本分类项目：基于预训练模型微调，F1 分数提升 {metric} 个百分点。",
    ],
    "数据": [
        "离线数仓建设：设计分层模型并补齐数据质量监控，报表产出时间缩短 {metric}%。",
        "用户增长看板：使用 SQL + Spark 构建指标体系，支撑 {metric} 个核心指标日报。",
    ],
    "测试": [
        "接口自动化体系：基于 Pytest 建设回归用例集，回归测试耗时缩短 {metric}%。",
        "性能测试专项：定位慢查询与连接池瓶颈，接口平均耗时下降 {metric}%。",
    ],
    "运维": [
        "容器化改造：将核心服务迁移至 Kubernetes，故障恢复时间缩短 {metric}%。",
        "监控告警体系：接入日志与指标监控，线上问题平均定位时间缩短 {metric}%。",
    ],
    "产品": [
        "招聘流程产品设计：梳理企业与学生双端流程，核心转化率提升 {metric}%。",
        "后台配置化改造：将运营规则沉淀为可配置能力，需求交付周期缩短 {metric}%。",
    ],
    "运营": [
        "校园活动运营：策划线上线下联动活动，活动参与率提升 {metric}%。",
        "用户分层运营：设计新人成长任务，次月留存提升 {metric}%。",
    ],
    "市场": [
        "品牌传播项目：统筹内容投放与达人合作，品牌曝光提升 {metric}%。",
        "渠道获客优化：重配投放预算与素材，获客成本降低 {metric}%。",
    ],
    "职能": [
        "校园招聘专项：优化宣讲与面试流程，招聘周期缩短 {metric}%。",
        "流程数字化：将审批与档案流程线上化，处理效率提升 {metric}%。",
    ],
}

LEVEL_PLAN = (
    [(track, "应届生") for track in TRACKS for _ in range(2)]
    + [(track, "初级工程师") for track in TRACKS]
    + [(track, "中级工程师") for track in TRACKS]
    + [
        ("后端", "高级工程师"),
        ("前端", "高级工程师"),
        ("算法", "高级工程师"),
        ("数据", "高级工程师"),
        ("测试", "高级工程师"),
        ("产品", "高级工程师"),
        ("后端", "高级工程师"),
    ]
    + [("后端", "技术管理"), ("产品", "技术管理"), ("运营", "技术管理")]
)

LEVEL_INFO = {
    "应届生": {
        "years": "应届",
        "salary": "8-15K",
        "degree": "本科",
        "grad": [2026, 2027],
    },
    "初级工程师": {
        "years": "1-2 年",
        "salary": "12-20K",
        "degree": "本科",
        "grad": [2024, 2025],
    },
    "中级工程师": {
        "years": "3-5 年",
        "salary": "20-30K",
        "degree": "本科",
        "grad": [2020, 2021, 2022],
    },
    "高级工程师": {
        "years": "6-10 年",
        "salary": "30-50K",
        "degree": "硕士",
        "grad": [2015, 2016, 2017, 2018, 2019],
    },
    "技术管理": {
        "years": "10 年以上",
        "salary": "40-70K",
        "degree": "硕士",
        "grad": [2008, 2010, 2012],
    },
}

PENDING_RESUME_INDEXES = {3, 9, 15, 22, 28, 35}
REJECTED_RESUME_INDEXES = {6, 18, 31, 44}

CULTURE_BY_INDUSTRY = {
    "互联网": "用户第一 · 坦诚协作 · 持续学习。以快速迭代和小步验证推动产品进化。",
    "人工智能": "求真 · 开放 · 长期主义。鼓励技术分享与论文复现，为新人配备导师。",
    "金融": "稳健 · 合规 · 专业。重视风险意识与专业沉淀，提供完整轮岗培养体系。",
    "制造业": "精益 · 务实 · 匠人精神。坚持现场主义，让校招生从真实产线中成长。",
    "消费品": "洞察用户 · 敏捷执行 · 结果导向。鼓励一线试错，用数据验证每个创意。",
    "医疗健康": "敬畏生命 · 严谨求证 · 协同共赢。以临床价值为第一判断标准。",
    "新能源": "创新驱动 · 安全至上 · 绿色使命。为校招生提供跨基地实践机会。",
}
DEFAULT_CULTURE = (
    "客户导向 · 团队协作 · 追求卓越。我们重视校招生培养，提供导师制与清晰的晋升通道。"
)


def _company_intro(company: dict) -> str:
    return (
        f"{company['name']}是一家深耕{company['industry']}领域的创新企业，"
        f"总部位于{company['city']}，团队规模 {company['size']}，"
        f"目前处于{company['funding']}阶段。公司坚持以技术与产品双轮驱动，"
        "为校招生提供导师制培养、真实业务场景与清晰的成长路径。"
    )


def _company_culture(company: dict) -> str:
    return CULTURE_BY_INDUSTRY.get(company["industry"], DEFAULT_CULTURE)


def _iso(days_ago: int = 0, hours_ago: int = 0) -> str:
    moment = datetime.now(CN_TZ) - timedelta(days=days_ago, hours=hours_ago)
    return moment.isoformat(timespec="seconds")


def _placeholders(values) -> str:
    return ",".join("?" * len(values))


def _clean_name(seed: dict) -> str:
    return (
        f"{seed['name']}（{seed['industry']}·{seed['size']}·"
        f"{seed['funding']}·{seed['city']}）"
    )


def _ensure_admin(conn) -> int:
    admin = query_one(
        conn, "SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
    )
    if admin is not None:
        return int(admin["id"])
    cursor = conn.execute(
        """
        INSERT INTO users
            (email, password_hash, role, display_name, is_active, created_at)
        VALUES (?, ?, 'admin', '平台管理员', 1, ?)
        """,
        (ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), _iso()),
    )
    return int(cursor.lastrowid)


def _clear_seed_data(conn) -> None:
    """只删除 @seed.campus 账号及其关联数据。"""
    seed_rows = conn.execute(
        "SELECT id FROM users WHERE email LIKE ?", (f"%{SEED_DOMAIN}",)
    ).fetchall()
    seed_user_ids = [int(row["id"]) for row in seed_rows]
    if not seed_user_ids:
        return

    user_ph = _placeholders(seed_user_ids)
    company_rows = conn.execute(
        f"SELECT id FROM companies WHERE user_id IN ({user_ph})", seed_user_ids
    ).fetchall()
    company_ids = [int(row["id"]) for row in company_rows]
    job_ids = []
    if company_ids:
        company_ph = _placeholders(company_ids)
        job_rows = conn.execute(
            f"SELECT id FROM jobs WHERE company_id IN ({company_ph})", company_ids
        ).fetchall()
        job_ids = [int(row["id"]) for row in job_rows]
    resume_rows = conn.execute(
        f"SELECT id FROM resumes WHERE student_id IN ({user_ph})", seed_user_ids
    ).fetchall()
    resume_ids = [int(row["id"]) for row in resume_rows]

    if job_ids:
        job_ph = _placeholders(job_ids)
        real_applications = conn.execute(
            f"""
            SELECT COUNT(*) AS total FROM applications
            WHERE job_id IN ({job_ph}) AND student_id NOT IN ({user_ph})
            """,
            job_ids + seed_user_ids,
        ).fetchone()["total"]
        if real_applications:
            raise RuntimeError(
                "检测到非种子学生投递了种子职位，已中止重置以避免影响真实数据"
            )

    if job_ids:
        conn.execute(
            f"DELETE FROM applications WHERE job_id IN ({_placeholders(job_ids)})",
            job_ids,
        )
    conn.execute(
        f"DELETE FROM applications WHERE student_id IN ({user_ph})", seed_user_ids
    )

    log_conditions = []
    log_params = []
    if company_ids:
        log_conditions.append(
            "entity_type IN ('company_license', 'company_hr') "
            f"AND entity_id IN ({_placeholders(company_ids)})"
        )
        log_params.extend(company_ids)
    if job_ids:
        log_conditions.append(
            f"entity_type = 'job' AND entity_id IN ({_placeholders(job_ids)})"
        )
        log_params.extend(job_ids)
    if resume_ids:
        log_conditions.append(
            f"entity_type = 'resume' AND entity_id IN ({_placeholders(resume_ids)})"
        )
        log_params.extend(resume_ids)
    if log_conditions:
        conn.execute(
            f"DELETE FROM review_logs WHERE {' OR '.join(log_conditions)}",
            log_params,
        )

    if company_ids:
        conn.execute(
            f"DELETE FROM jobs WHERE company_id IN ({_placeholders(company_ids)})",
            company_ids,
        )
        conn.execute(
            f"DELETE FROM companies WHERE id IN ({_placeholders(company_ids)})",
            company_ids,
        )
    conn.execute(f"DELETE FROM resumes WHERE student_id IN ({user_ph})", seed_user_ids)
    conn.execute(
        f"DELETE FROM users WHERE id IN ({_placeholders(seed_user_ids)})",
        seed_user_ids,
    )


def _build_profiles() -> list[dict]:
    profiles = []
    for index, (track, level) in enumerate(LEVEL_PLAN):
        info = LEVEL_INFO[level]
        years = info["years"]
        grad = info["grad"][index % len(info["grad"])]
        school = SCHOOLS[index % len(SCHOOLS)]
        majors = TRACK_MAJORS[track]
        major = majors[index % len(majors)]
        city = CITIES[index % len(CITIES)]
        skills = TRACK_SKILLS[track]
        metric = 70 + (index * 7) % 60
        projects = TRACK_PROJECTS[track]
        project_one = projects[index % len(projects)].format(metric=metric)
        project_two = projects[(index + 1) % len(projects)].format(metric=metric + 5)

        if level == "技术管理":
            self_eval = "具备团队管理与跨部门协作经验，能推动复杂项目按目标落地。"
        elif level == "高级工程师":
            self_eval = "具备复杂系统设计与技术攻坚能力，能带动团队提升工程效率。"
        elif level == "中级工程师":
            self_eval = "能独立负责模块设计与交付，注重代码质量与线上稳定性。"
        elif level == "初级工程师":
            self_eval = "具备扎实的工程基础，能在指导下独立完成模块开发。"
        else:
            self_eval = "学习能力强，参与过完整课程项目，希望在实践中快速成长。"

        summary = "\n".join(
            [
                (
                    f"【层级】{level}｜应届"
                    if years == "应届"
                    else f"【层级】{level}｜{years}经验"
                ),
                f"【期望薪资】{info['salary']}｜期望城市：{city}",
                f"【教育背景】{school} · {major} · {info['degree']} · {grad} 届",
                f"【技能栈】{' / '.join(skills)}",
                "【项目经历】",
                f"1. {project_one}",
                f"2. {project_two}",
                f"【自我评价】{self_eval}",
            ]
        )

        profiles.append(
            {
                "index": index,
                "email": f"student{index + 1:02d}{SEED_DOMAIN}",
                "name": NAMES[index],
                "phone": f"138{index + 1:08d}",
                "school": school,
                "major": major,
                "grad": grad,
                "city": city,
                "level": level,
                "track": track,
                "skills": " / ".join(skills),
                "summary": summary,
                "status": (
                    "PENDING"
                    if index in PENDING_RESUME_INDEXES
                    else "REJECTED"
                    if index in REJECTED_RESUME_INDEXES
                    else "VERIFIED"
                ),
            }
        )
    return profiles


def _build_job_description(job: dict, company: dict) -> str:
    type_label = "校招" if job["type"] == "CAMPUS" else "实习"
    return "\n".join(
        [
            f"【岗位标签】{job['category']}/{job['track']}/{type_label}",
            f"【招聘需求】{job['need']}",
            (
                f"【团队介绍】{company['name']} {company['industry']}团队，"
                "负责核心业务建设与持续迭代。"
            ),
            f"【公司福利】{company['benefits']}",
        ]
    )


def _build_job_requirements(job: dict) -> str:
    return "\n".join(
        [
            "【任职要求】",
            job["req"],
            "【加分项】有相关实习、竞赛或开源项目经历者优先。",
        ]
    )


def _insert_review_log(
    conn,
    entity_type: str,
    entity_id: int,
    decision: str,
    note: str | None,
    admin_id: int,
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO review_logs
            (entity_type, entity_id, decision, note, reviewer_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (entity_type, entity_id, decision, note, admin_id, created_at),
    )


def seed(db_path: Path | str | None = None) -> dict:
    """重建全部种子数据，返回各类数据量。"""
    init_db(db_path)
    student_hash = hash_password(STUDENT_PASSWORD)
    company_hash = hash_password(COMPANY_PASSWORD)
    profiles = _build_profiles()

    with get_connection(db_path) as conn:
        admin_id = _ensure_admin(conn)
        _clear_seed_data(conn)

        company_ids = []
        for index, company in enumerate(COMPANY_SEEDS, start=1):
            cursor = conn.execute(
                """
                INSERT INTO users
                    (email, password_hash, role, display_name, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    f"company{index:02d}{SEED_DOMAIN}",
                    company_hash,
                    Role.COMPANY.value,
                    company["name"],
                    _iso(days_ago=60 - index),
                ),
            )
            company_user_id = int(cursor.lastrowid)
            company_cursor = conn.execute(
                """
                INSERT INTO companies
                    (user_id, name, license_no, license_file, hr_name, hr_email,
                     hr_proof_file, logo_path, intro, culture, industry,
                     company_size, funding_stage, city, benefits,
                     status, hr_status, created_at, updated_at)
                VALUES (?, ?, ?, NULL, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?)
                """,
                (
                    company_user_id,
                    _clean_name(company),
                    f"91310000SEED{index:04d}X",
                    company["hr"],
                    f"hr{index:02d}{SEED_DOMAIN}",
                    _company_intro(company),
                    _company_culture(company),
                    company["industry"],
                    company["size"],
                    company["funding"],
                    company["city"],
                    company["benefits"],
                    company["status"],
                    company["hr_status"],
                    _iso(days_ago=60 - index),
                    _iso(days_ago=55 - index),
                ),
            )
            company_ids.append(int(company_cursor.lastrowid))

            if company["status"] in {"APPROVED", "REJECTED"}:
                _insert_review_log(
                    conn,
                    "company_license",
                    int(company_cursor.lastrowid),
                    company["status"],
                    company["note"],
                    admin_id,
                    _iso(days_ago=54 - index),
                )
            if company["hr_status"] in {"APPROVED", "REJECTED"}:
                _insert_review_log(
                    conn,
                    "company_hr",
                    int(company_cursor.lastrowid),
                    company["hr_status"],
                    None,
                    admin_id,
                    _iso(days_ago=53 - index),
                )

        resume_ids = []
        for profile in profiles:
            user_cursor = conn.execute(
                """
                INSERT INTO users
                    (email, password_hash, role, display_name, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    profile["email"],
                    student_hash,
                    Role.STUDENT.value,
                    profile["name"],
                    _iso(days_ago=45 - (profile["index"] % 30)),
                ),
            )
            student_id = int(user_cursor.lastrowid)
            resume_cursor = conn.execute(
                """
                INSERT INTO resumes
                    (student_id, real_name, phone, school, major, graduation_year,
                     skills, summary, file_path, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    student_id,
                    profile["name"],
                    profile["phone"],
                    profile["school"],
                    profile["major"],
                    profile["grad"],
                    profile["skills"],
                    profile["summary"],
                    profile["status"],
                    _iso(days_ago=40 - (profile["index"] % 25)),
                ),
            )
            profile["student_id"] = student_id
            profile["resume_id"] = int(resume_cursor.lastrowid)
            resume_ids.append(int(resume_cursor.lastrowid))

            if profile["status"] == "VERIFIED":
                _insert_review_log(
                    conn,
                    "resume",
                    int(resume_cursor.lastrowid),
                    "VERIFIED",
                    None,
                    admin_id,
                    _iso(days_ago=39 - (profile["index"] % 20)),
                )
            elif profile["status"] == "REJECTED":
                _insert_review_log(
                    conn,
                    "resume",
                    int(resume_cursor.lastrowid),
                    "REJECTED",
                    "项目经历描述较简单，请补充职责与量化结果后重新提交",
                    admin_id,
                    _iso(days_ago=38 - (profile["index"] % 20)),
                )

        jobs = []
        for index, job in enumerate(JOB_SEEDS, start=1):
            company = COMPANY_SEEDS[job["company"] - 1]
            company_id = company_ids[job["company"] - 1]
            type_label = "校招" if job["type"] == "CAMPUS" else "实习"
            cursor = conn.execute(
                """
                INSERT INTO jobs
                    (company_id, title, job_type, city, salary, description,
                     requirements, status, is_featured, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    f"【{job['category']}】{job['title']}（{type_label}）",
                    job["type"],
                    company["city"],
                    job["salary"],
                    _build_job_description(job, company),
                    _build_job_requirements(job),
                    job["status"],
                    1 if job.get("featured") else 0,
                    _iso(days_ago=30 - (index % 25)),
                    _iso(days_ago=29 - (index % 25)),
                ),
            )
            job_id = int(cursor.lastrowid)
            job["job_id"] = job_id
            jobs.append(job)

            if job["status"] in {"APPROVED", "REJECTED", "CLOSED"}:
                decision = "REJECTED" if job["status"] == "REJECTED" else "APPROVED"
                _insert_review_log(
                    conn,
                    "job",
                    job_id,
                    decision,
                    job.get("note"),
                    admin_id,
                    _iso(days_ago=28 - (index % 20)),
                )

        eligible_levels = {"应届生", "初级工程师", "中级工程师"}
        eligible_by_track: dict[str, list[dict]] = {track: [] for track in TRACKS}
        eligible_all = []
        for profile in profiles:
            if profile["status"] != "VERIFIED":
                continue
            if profile["level"] in eligible_levels:
                eligible_by_track[profile["track"]].append(profile)
                eligible_all.append(profile)

        application_statuses = [
            "SUBMITTED",
            "VIEWED",
            "SHORTLISTED",
            "HIRED",
            "REJECTED",
        ]
        feedbacks = {
            "SUBMITTED": None,
            "VIEWED": None,
            "SHORTLISTED": "简历通过初筛，已进入面试环节，请留意后续通知。",
            "HIRED": "综合评估通过，欢迎加入团队！",
            "REJECTED": "本轮岗位匹配度不足，感谢你的关注。",
        }

        application_count = 0
        approved_jobs = [job for job in jobs if job["status"] == "APPROVED"]
        for job_index, job in enumerate(approved_jobs):
            pool = eligible_by_track.get(job["track"], [])
            if job["type"] == "INTERN":
                fresher_pool = [
                    profile for profile in pool if profile["level"] == "应届生"
                ]
                if fresher_pool:
                    pool = fresher_pool
            offset = job_index % len(pool) if pool else 0
            ordered = pool[offset:] + pool[:offset] if pool else []
            chosen = []
            for profile in ordered + eligible_all:
                if profile in chosen:
                    continue
                chosen.append(profile)
                if len(chosen) == 4:
                    break

            for slot, profile in enumerate(chosen):
                status = application_statuses[
                    (job_index + slot) % len(application_statuses)
                ]
                snapshot = json.dumps(
                    {
                        "id": profile["resume_id"],
                        "real_name": profile["name"],
                        "phone": profile["phone"],
                        "school": profile["school"],
                        "major": profile["major"],
                        "graduation_year": profile["grad"],
                        "skills": profile["skills"],
                        "summary": profile["summary"],
                        "file_path": None,
                        "status": "VERIFIED",
                        "updated_at": _iso(days_ago=40 - (profile["index"] % 25)),
                    },
                    ensure_ascii=False,
                )
                conn.execute(
                    """
                    INSERT INTO applications
                        (job_id, student_id, resume_id, resume_snapshot,
                         resume_file_snapshot, status, feedback, created_at, updated_at)
                    VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        job["job_id"],
                        profile["student_id"],
                        profile["resume_id"],
                        snapshot,
                        status,
                        feedbacks[status],
                        _iso(days_ago=14 - (job_index % 12), hours_ago=slot),
                        _iso(days_ago=10 - (job_index % 8), hours_ago=slot),
                    ),
                )
                application_count += 1

        favorite_count = 0
        approved_job_ids = [job["job_id"] for job in approved_jobs]
        verified_profiles = [
            profile for profile in profiles if profile["status"] == "VERIFIED"
        ]
        for index, profile in enumerate(verified_profiles[:15]):
            applied_ids = {
                row["job_id"]
                for row in conn.execute(
                    "SELECT job_id FROM applications WHERE student_id = ?",
                    (profile["student_id"],),
                ).fetchall()
            }
            picks: list[int] = []
            for step in range(len(approved_job_ids)):
                job_id = approved_job_ids[(index * 3 + step) % len(approved_job_ids)]
                if job_id in applied_ids or job_id in picks:
                    continue
                picks.append(job_id)
                if len(picks) == 3:
                    break
            for slot, job_id in enumerate(picks):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO favorites
                        (student_id, job_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        profile["student_id"],
                        job_id,
                        _iso(days_ago=5 - (slot % 5), hours_ago=index),
                    ),
                )
                favorite_count += 1

        urgent_until = (datetime.now(CN_TZ) + timedelta(days=7)).date().isoformat()
        for job in approved_jobs[:2]:
            conn.execute(
                "UPDATE jobs SET is_urgent = 1, urgent_until = ? WHERE id = ?",
                (urgent_until, job["job_id"]),
            )

        view_count = 0
        for index, profile in enumerate(verified_profiles[:12]):
            job = approved_jobs[index % len(approved_jobs)]
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO job_views (job_id, student_id, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    job["job_id"],
                    profile["student_id"],
                    _iso(days_ago=3, hours_ago=index),
                ),
            )
            view_count += cursor.rowcount

        culture_samples = [
            (
                "CURRENT",
                "experience",
                "技术团队的真实工作节奏",
                "入职半年，团队采用双周迭代，需求评审和复盘都比较规范。"
                "导师制落地，新人前两个月有明确的学习计划，整体节奏可控。",
            ),
            (
                "FORMER",
                "experience",
                "实习转正的真实体验",
                "实习三个月后转正，面试流程规范，转正答辩有明确标准。"
                "福利发放及时，团队沟通直接，适合想快速成长的应届生。",
            ),
            (
                "INTERN",
                "question",
                "想了解暑期实习的培养机制",
                "请问暑期实习生是否有独立项目？导师带教比例大概是多少？",
            ),
        ]
        culture_count = 0
        for index, (employment, topic, title, content) in enumerate(culture_samples):
            job = approved_jobs[index % len(approved_jobs)]
            company_id = company_ids[job["company"] - 1]
            profile = verified_profiles[index]
            conn.execute(
                """
                INSERT INTO culture_posts
                    (company_id, user_id, employment_status, is_verified,
                     is_anonymous, topic, title, content, status,
                     official_reply, created_at, updated_at)
                VALUES (?, ?, ?, 1, 1, ?, ?, ?, 'APPROVED', NULL, ?, ?)
                """,
                (
                    company_id,
                    profile["student_id"],
                    employment,
                    topic,
                    title,
                    content,
                    _iso(days_ago=9 - index),
                    _iso(days_ago=8 - index),
                ),
            )
            culture_count += 1

        review_samples = [
            (
                "CURRENT",
                5,
                4,
                3,
                5,
                5,
                "团队成长空间大，导师愿意花时间带新人，项目节奏合理。"
                "薪酬福利在同类公司中有竞争力，面试流程清晰，推荐投递。",
            ),
            (
                "FORMER",
                4,
                4,
                4,
                4,
                4,
                "在职期间负责独立模块，能接触到完整业务链路。"
                "加班情况因项目而异，福利发放及时，整体体验符合预期。",
            ),
            (
                "INTERN",
                4,
                3,
                3,
                5,
                4,
                "实习期间有明确任务清单和周会反馈，能快速了解工程流程。"
                "转正答辩标准透明，适合希望积累项目经验的在校生。",
            ),
            (
                "CURRENT",
                4,
                4,
                3,
                4,
                4,
                "公司氛围开放，跨部门协作顺畅，技术分享频率较高。"
                "福利体系完善，年度调薪机制透明，整体推荐。",
            ),
        ]
        review_count = 0
        for index, sample in enumerate(review_samples):
            (
                employment,
                growth,
                salary,
                intensity,
                interview,
                recommend,
                content,
            ) = sample
            profile = verified_profiles[index]
            company_id = company_ids[0] if index < 3 else company_ids[1]
            conn.execute(
                """
                INSERT OR IGNORE INTO company_reviews
                    (company_id, user_id, employment_status, growth, salary,
                     intensity, interview, recommend, content, status,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?, ?)
                """,
                (
                    company_id,
                    profile["student_id"],
                    employment,
                    growth,
                    salary,
                    intensity,
                    interview,
                    recommend,
                    content,
                    _iso(days_ago=12 - index),
                    _iso(days_ago=11 - index),
                ),
            )
            review_count += 1

        task_samples = [
            (
                0,
                "校园开放日现场协助",
                "负责签到引导、物料发放与现场秩序维护，提供工作餐与交通补贴，"
                "需提前半小时到场参加简短培训。",
                "150 元/天",
                "周六 9:00-17:00",
                8,
                "APPROVED",
            ),
            (
                1,
                "展会资料整理与派发",
                "在企业展台协助资料整理与访客引导，工作内容简单，提供统一服装与午餐。",
                "180 元/天",
                "周日 10:00-16:00",
                10,
                "APPROVED",
            ),
            (
                2,
                "产品调研问卷访问",
                "协助完成线上问卷的受访者联系与记录，按有效问卷结算，全程线上完成。",
                "80 元/次",
                "一周内灵活安排",
                20,
                "PENDING",
            ),
        ]
        task_count = 0
        for (
            company_slot,
            title,
            description,
            reward,
            schedule,
            headcount,
            status,
        ) in task_samples:
            conn.execute(
                """
                INSERT INTO micro_tasks
                    (company_id, title, description, city, reward, schedule,
                     headcount, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_ids[company_slot],
                    title,
                    description,
                    COMPANY_SEEDS[company_slot]["city"],
                    reward,
                    schedule,
                    headcount,
                    status,
                    _iso(days_ago=6 - company_slot),
                    _iso(days_ago=5 - company_slot),
                ),
            )
            task_count += 1

        return {
            "admin_id": admin_id,
            "companies": len(COMPANY_SEEDS),
            "students": len(profiles),
            "resumes": len(resume_ids),
            "jobs": len(JOB_SEEDS),
            "applications": application_count,
            "favorites": favorite_count,
            "culture_posts": culture_count,
            "company_reviews": review_count,
            "micro_tasks": task_count,
            "job_views": view_count,
            "review_logs": conn.execute(
                "SELECT COUNT(*) AS total FROM review_logs"
            ).fetchone()["total"],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="导入模拟测试与演示数据")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="目标数据库路径，默认使用 data/app.db",
    )
    args = parser.parse_args()

    summary = seed(args.db_path)
    print("模拟数据已导入（重复执行会先清理旧种子数据）：")
    print(f"  企业：{summary['companies']} 家")
    print(f"  学生/简历：{summary['students']} 人 / {summary['resumes']} 份")
    print(f"  岗位：{summary['jobs']} 个")
    print(f"  投递：{summary['applications']} 条")
    print(f"  收藏：{summary['favorites']} 条")
    print(
        f"  社区：文化帖 {summary['culture_posts']} 条 / "
        f"企业评分 {summary['company_reviews']} 条 / "
        f"小任务 {summary['micro_tasks']} 个 / 浏览 {summary['job_views']} 条"
    )
    print(f"  审核日志：{summary['review_logs']} 条")
    print("演示账号：")
    print(f"  学生：student01{SEED_DOMAIN} / {STUDENT_PASSWORD}")
    print(f"  企业：company01{SEED_DOMAIN} / {COMPANY_PASSWORD}")


if __name__ == "__main__":
    main()
