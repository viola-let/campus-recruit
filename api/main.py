"""FastAPI 应用：CORS、路由注册、健康检查与统一业务错误响应。"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import (
    admin,
    applications,
    auth,
    community,
    companies,
    jobs,
    students,
)
from core.errors import BusinessError

# 业务错误码 → HTTP 状态码；未列出的统一按 400 处理
ERROR_STATUS_CODES = {
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "EMAIL_EXISTS": 409,
    "DUPLICATE_APPLICATION": 409,
    "DUPLICATE_REVIEW": 409,
    "DUPLICATE_SIGNUP": 409,
    "DUPLICATE_CONTENT": 409,
    "TASK_FULL": 409,
}

app = FastAPI(
    title="CampusRecruit API",
    version="1.2.0",
    description="校招平台 REST 适配层，业务规则与 Streamlit 页面共用 services/。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BusinessError)
async def handle_business_error(request: Request, exc: BusinessError) -> JSONResponse:
    """把 BusinessError 转换为 {code, message} 响应。"""
    return JSONResponse(
        status_code=ERROR_STATUS_CODES.get(exc.code, 400),
        content={"code": exc.code, "message": exc.message},
    )


@app.get("/health", tags=["运维"])
def health() -> dict:
    return {"status": "ok"}


for router in (
    auth.router,
    students.router,
    jobs.router,
    companies.router,
    applications.router,
    admin.router,
    community.router,
):
    app.include_router(router, prefix="/api/v1")
