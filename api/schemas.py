"""API 请求 / 响应模型（Pydantic）。"""

from typing import Literal

from pydantic import BaseModel


class RegisterStudentRequest(BaseModel):
    email: str
    password: str
    display_name: str


class RegisterCompanyRequest(BaseModel):
    email: str
    password: str
    company_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    display_name: str
    is_active: int


class ResumePayload(BaseModel):
    real_name: str
    phone: str
    school: str
    major: str
    graduation_year: int
    skills: str = ""
    summary: str = ""


class CompanyProfilePayload(BaseModel):
    name: str
    license_no: str
    hr_name: str
    hr_email: str


class CompanyBrandingPayload(BaseModel):
    intro: str = ""
    culture: str = ""
    industry: str = ""
    company_size: str = ""
    funding_stage: str = ""
    city: str = ""
    benefits: str = ""


class BatchApplyRequest(BaseModel):
    job_ids: list[int]


class CompanyReviewPayload(BaseModel):
    employment_status: str
    growth: int
    salary: int
    intensity: int
    interview: int
    recommend: int
    content: str


class CulturePostPayload(BaseModel):
    company_id: int
    employment_status: str
    topic: str
    title: str
    content: str
    anonymous: bool = True


class JobPayload(BaseModel):
    title: str
    job_type: Literal["CAMPUS", "INTERN"]
    city: str
    salary: str = ""
    description: str
    requirements: str = ""


class JobPatchRequest(BaseModel):
    action: Literal["edit", "close", "reopen"]
    job: JobPayload | None = None


class ApplicationStatusRequest(BaseModel):
    new_status: str
    feedback: str | None = None


class ReviewRequest(BaseModel):
    decision: str
    note: str | None = None
    featured: bool | None = None
