"""认证路由：注册、登录、当前用户。"""

from fastapi import APIRouter, Depends

from api.deps import get_current_user
from api.schemas import (
    LoginRequest,
    RegisterCompanyRequest,
    RegisterStudentRequest,
    TokenResponse,
    UserOut,
)
from core import auth
from core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register/student", response_model=UserOut, status_code=201)
def register_student(payload: RegisterStudentRequest) -> dict:
    user_id = auth.register_student(
        payload.email, payload.password, payload.display_name
    )
    return auth.get_user(user_id)


@router.post("/register/company", response_model=UserOut, status_code=201)
def register_company(payload: RegisterCompanyRequest) -> dict:
    user_id = auth.register_company(
        payload.email, payload.password, payload.company_name
    )
    return auth.get_user(user_id)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> dict:
    user = auth.login(payload.email, payload.password)
    token, expires_in = create_access_token(user["id"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
    }


@router.get("/me", response_model=UserOut)
def read_me(user: dict = Depends(get_current_user)) -> dict:
    return user
