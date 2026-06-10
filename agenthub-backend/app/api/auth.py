from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import LoginOut, UserLoginRequest, UserOut, UserRegisterRequest
from app.services.auth_service import login, register


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[LoginOut])
def login_api(payload: UserLoginRequest, db: Session = Depends(get_db)):
    token, user = login(db, payload.email, payload.password)
    return ApiResponse(data=LoginOut(access_token=token, user=UserOut.model_validate(user)))


@router.post("/register", response_model=ApiResponse[LoginOut])
def register_api(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    token, user = register(
        db,
        email=payload.email,
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
        bio=payload.bio,
    )
    return ApiResponse(data=LoginOut(access_token=token, user=UserOut.model_validate(user)))


@router.get("/me", response_model=ApiResponse[UserOut])
def me_api(current_user: User = Depends(get_current_user)):
    return ApiResponse(data=UserOut.model_validate(current_user))
