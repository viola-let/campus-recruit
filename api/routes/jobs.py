"""职位路由：职位广场、详情、相似推荐、批量投递与收藏。"""

from fastapi import APIRouter, Depends, Query

from api.deps import require_role
from api.schemas import BatchApplyRequest
from core.errors import BusinessError
from services import applications, favorites, jobs, recommendations

router = APIRouter(prefix="/jobs", tags=["职位"])


@router.get("")
def list_jobs(
    keyword: str | None = None,
    city: str | None = None,
    job_type: str | None = None,
    category: str | None = None,
    search_field: str = Query("all", pattern="^(all|title)$"),
    sort: str = Query("featured", pattern="^(featured|latest|salary)$"),
    only_urgent: bool = False,
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(require_role("student", "admin")),
) -> list[dict]:
    return jobs.search_jobs(
        keyword=keyword,
        city=city,
        job_type=job_type,
        category=category,
        search_field=search_field,
        sort=sort,
        only_urgent=only_urgent,
        limit=limit,
    )


@router.get("/recommendations")
def read_recommendations(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(require_role("student")),
) -> list[dict]:
    """基于简历画像的智能推荐。"""
    return recommendations.recommend_jobs(user["id"], limit=limit)


@router.get("/favorites")
def read_favorites(user: dict = Depends(require_role("student"))) -> list[dict]:
    """我收藏的职位。"""
    return favorites.list_favorites(user["id"])


@router.post("/batch-applications", status_code=201)
def batch_apply(
    payload: BatchApplyRequest, user: dict = Depends(require_role("student"))
) -> dict:
    """批量投递：最多 20 个职位，返回逐个结果。"""
    return applications.batch_apply_to_job(user["id"], payload.job_ids)


@router.get("/{job_id}")
def read_job(
    job_id: int, user: dict = Depends(require_role("student", "admin"))
) -> dict:
    job = jobs.get_public_job(job_id)
    if job is None:
        raise BusinessError("NOT_FOUND", "职位不存在或已关闭")
    return job


@router.get("/{job_id}/similar")
def read_similar_jobs(
    job_id: int,
    limit: int = Query(5, ge=1, le=20),
    user: dict = Depends(require_role("student", "admin")),
) -> list[dict]:
    if jobs.get_public_job(job_id) is None:
        raise BusinessError("NOT_FOUND", "职位不存在或已关闭")
    return jobs.similar_jobs(job_id, limit=limit)


@router.post("/{job_id}/favorite")
def toggle_favorite(job_id: int, user: dict = Depends(require_role("student"))) -> dict:
    """收藏 / 取消收藏，返回切换后的状态。"""
    favorited = favorites.toggle_favorite(user["id"], job_id)
    return {"job_id": job_id, "favorited": favorited}


@router.post("/{job_id}/applications", status_code=201)
def apply_to_job(job_id: int, user: dict = Depends(require_role("student"))) -> dict:
    return applications.apply_to_job(user["id"], job_id)
