"""投递路由：状态流转与简历附件下载。"""

from fastapi import APIRouter, Depends, Response

from api.deps import require_role
from api.schemas import ApplicationStatusRequest
from services import applications

router = APIRouter(prefix="/applications", tags=["投递"])


@router.patch("/{application_id}/status")
def update_application_status(
    application_id: int,
    payload: ApplicationStatusRequest,
    user: dict = Depends(require_role("company")),
) -> dict:
    return applications.update_status(
        user["id"], application_id, payload.new_status, payload.feedback
    )


@router.get("/{application_id}/resume-file")
def download_resume_file(
    application_id: int,
    user: dict = Depends(require_role("company", "admin")),
) -> Response:
    filename, data = applications.get_resume_file(user["id"], application_id)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
