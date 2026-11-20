"""管理端路由：统计、待办与四层审核。"""

from fastapi import APIRouter, Depends, Query

from api.deps import require_role
from api.schemas import ReviewRequest
from core.config import JobStatus
from services import admin, companies, jobs, students

router = APIRouter(prefix="/admin", tags=["管理端"])
admin_only = require_role("admin")


@router.get("/dashboard")
def read_dashboard(user: dict = Depends(admin_only)) -> dict:
    return admin.dashboard_counts(user["id"])


@router.get("/pending")
def read_pending(
    limit: int = Query(20, ge=1, le=200),
    user: dict = Depends(admin_only),
) -> dict:
    return admin.pending_queues(user["id"], limit=limit)


@router.post("/companies/{company_id}/license/review")
def review_company_license(
    company_id: int,
    payload: ReviewRequest,
    user: dict = Depends(admin_only),
) -> dict:
    return companies.review_license(
        user["id"], company_id, payload.decision, payload.note
    )


@router.post("/companies/{company_id}/hr/review")
def review_company_hr(
    company_id: int,
    payload: ReviewRequest,
    user: dict = Depends(admin_only),
) -> dict:
    return companies.review_hr(user["id"], company_id, payload.decision, payload.note)


@router.post("/jobs/{job_id}/review")
def review_job(
    job_id: int,
    payload: ReviewRequest,
    user: dict = Depends(admin_only),
) -> dict:
    job = jobs.review_job(user["id"], job_id, payload.decision, payload.note)
    if payload.featured is not None and job["status"] == JobStatus.APPROVED.value:
        jobs.set_featured(user["id"], job_id, payload.featured)
        job["is_featured"] = 1 if payload.featured else 0
    return job


@router.post("/resumes/{resume_id}/review")
def review_resume(
    resume_id: int,
    payload: ReviewRequest,
    user: dict = Depends(admin_only),
) -> dict:
    return students.review_resume(user["id"], resume_id, payload.decision, payload.note)
