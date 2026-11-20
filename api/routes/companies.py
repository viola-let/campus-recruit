"""企业路由：资料、证明材料、职位与候选人。"""

from fastapi import APIRouter, Depends, File, Query, UploadFile

from api.deps import require_role
from api.schemas import (
    CompanyBrandingPayload,
    CompanyProfilePayload,
    JobPatchRequest,
    JobPayload,
)
from core.errors import BusinessError
from services import applications, companies, jobs

router = APIRouter(prefix="/companies", tags=["企业"])
company_only = require_role("company")


@router.get("/me")
def read_my_company(user: dict = Depends(company_only)) -> dict:
    profile = companies.get_profile(user["id"])
    if profile is None:
        raise BusinessError("NOT_FOUND", "企业资料不存在")
    return profile


@router.put("/me")
def update_my_company(
    payload: CompanyProfilePayload, user: dict = Depends(company_only)
) -> dict:
    return companies.upsert_profile(user["id"], payload.model_dump())


@router.post("/me/files/{kind}", status_code=201)
async def upload_company_file(
    kind: str,
    file: UploadFile = File(...),
    user: dict = Depends(company_only),
) -> dict:
    content = await file.read()
    relative_path = companies.attach_company_file(
        user["id"], kind, file.filename or "", content
    )
    return {"file_path": relative_path}


@router.put("/me/branding")
def update_my_branding(
    payload: CompanyBrandingPayload, user: dict = Depends(company_only)
) -> dict:
    """更新企业品牌展示信息（logo 请使用 /me/logo 上传）。"""
    return companies.update_branding(user["id"], payload.model_dump())


@router.post("/me/logo", status_code=201)
async def upload_my_logo(
    file: UploadFile = File(...),
    user: dict = Depends(company_only),
) -> dict:
    content = await file.read()
    relative_path = companies.attach_logo(user["id"], file.filename or "", content)
    return {"logo_path": relative_path}


@router.get("/me/jobs")
def read_my_jobs(
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(company_only),
) -> list[dict]:
    return jobs.list_company_jobs(user["id"], limit=limit)


@router.post("/me/jobs", status_code=201)
def create_my_job(payload: JobPayload, user: dict = Depends(company_only)) -> dict:
    return jobs.create_job(user["id"], payload.model_dump())


@router.patch("/me/jobs/{job_id}")
def patch_my_job(
    job_id: int,
    payload: JobPatchRequest,
    user: dict = Depends(company_only),
) -> dict:
    if payload.action == "close":
        jobs.close_job(user["id"], job_id)
        return {"id": job_id, "status": "CLOSED"}
    if payload.action == "reopen":
        return jobs.reopen_job(user["id"], job_id)
    if payload.job is None:
        raise BusinessError("VALIDATION_ERROR", "编辑职位时必须提供职位内容")
    return jobs.update_job(user["id"], job_id, payload.job.model_dump())


@router.get("/me/candidates")
def read_my_candidates(
    job_id: int | None = None,
    school: str | None = None,
    major: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    user: dict = Depends(company_only),
) -> list[dict]:
    filters = {
        "job_id": job_id,
        "school": school,
        "major": major,
        "status": status,
    }
    return applications.list_job_candidates(user["id"], filters, limit=limit)
