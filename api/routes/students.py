"""学生路由：本人简历、附件与投递列表。"""

from fastapi import APIRouter, Depends, File, UploadFile

from api.deps import require_role
from api.schemas import ResumePayload
from core.errors import BusinessError
from services import applications, students

router = APIRouter(prefix="/students", tags=["学生"])
student_only = require_role("student")


@router.get("/me/resume")
def read_my_resume(user: dict = Depends(student_only)) -> dict:
    resume = students.get_resume(user["id"])
    if resume is None:
        raise BusinessError("NOT_FOUND", "简历不存在")
    return resume


@router.put("/me/resume")
def save_my_resume(payload: ResumePayload, user: dict = Depends(student_only)) -> dict:
    return students.save_resume(user["id"], payload.model_dump())


@router.post("/me/resume/file", status_code=201)
async def upload_my_resume_file(
    file: UploadFile = File(...), user: dict = Depends(student_only)
) -> dict:
    content = await file.read()
    relative_path = students.attach_resume_file(
        user["id"], file.filename or "", content
    )
    return {"file_path": relative_path}


@router.get("/me/applications")
def read_my_applications(user: dict = Depends(student_only)) -> list[dict]:
    return applications.list_my_applications(user["id"])
