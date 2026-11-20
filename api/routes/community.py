"""社区路由：企业文化帖、企业评分与小任务。"""

from fastapi import APIRouter, Depends, Query

from api.deps import require_role
from api.schemas import CompanyReviewPayload, CulturePostPayload
from services import culture, micro_tasks, reviews

router = APIRouter(tags=["社区与口碑"])


@router.get("/culture-posts")
def list_culture_posts(
    company_id: int,
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("student", "admin")),
) -> list[dict]:
    """企业已通过的文化交流帖。"""
    return culture.list_company_posts(company_id, limit=limit)


@router.post("/culture-posts", status_code=201)
def create_culture_post(
    payload: CulturePostPayload, user: dict = Depends(require_role("student"))
) -> dict:
    """学生发布经验或提问，进入待审核队列。"""
    return culture.create_post(user["id"], payload.company_id, payload.model_dump())


@router.get("/companies/{company_id}/reviews")
def read_company_reviews(
    company_id: int,
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("student", "admin")),
) -> dict:
    """企业口碑聚合与已通过评价列表。"""
    return {
        "summary": reviews.rating_summary(company_id),
        "items": reviews.list_company_reviews(company_id, limit=limit),
    }


@router.post("/companies/{company_id}/reviews", status_code=201)
def create_company_review(
    company_id: int,
    payload: CompanyReviewPayload,
    user: dict = Depends(require_role("student")),
) -> dict:
    """在职 / 曾任职 / 实习过的学生提交多维度评分。"""
    return reviews.submit_review(user["id"], company_id, payload.model_dump())


@router.get("/micro-tasks")
def read_micro_tasks(
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("student", "admin")),
) -> list[dict]:
    """招募中的小任务列表。"""
    return micro_tasks.list_open_tasks(limit=limit)


@router.post("/micro-tasks/{task_id}/signup", status_code=201)
def signup_micro_task(
    task_id: int, user: dict = Depends(require_role("student"))
) -> dict:
    """学生报名小任务。"""
    return micro_tasks.signup_task(user["id"], task_id)
