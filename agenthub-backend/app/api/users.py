from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.services.storage_init_service import ensure_user_space
from app.services.storage_paths import user_dir
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreateRequest, UserOut, UserProfileMdOut, UserSelfUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=ApiResponse[list[UserOut]])
def list_users_api(
    q: str | None = Query(None, description="Search by email/username/display_name"),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        keyword = q.strip()
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                (User.email.ilike(like)) | (User.username.ilike(like)) | (User.display_name.ilike(like))
            )
    rows = query.order_by(User.id.asc()).all()
    return ApiResponse(data=[UserOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[UserOut])
def create_user_api(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
):
    # Minimal admin-less create for demo; production should validate + hash password.
    email = payload.email
    username =payload.username
    password = payload.password
    display_name = payload.display_name
    status_value = payload.status
    bio = payload.bio
    role = payload.role

    if not email or not username or not password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email/username/password required")

    exists = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email or username already exists")

    row = User(
        email=email,
        username=username,
        password=password,
        display_name=display_name,
        status=status_value,
        bio=bio,
        role=role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    ensure_user_space(int(row.id))
    return ApiResponse(data=UserOut.model_validate(row))


@router.get("/me", response_model=ApiResponse[UserOut])
def get_my_user_api(current_user: User = Depends(get_current_user)):
    return ApiResponse(data=UserOut.model_validate(current_user))


@router.put("/me", response_model=ApiResponse[UserOut])
def update_my_user_api(
    payload: UserSelfUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(User).filter(User.id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    row.display_name = payload.display_name
    row.bio = payload.bio
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiResponse(data=UserOut.model_validate(row))


def _profile_md_path(user_id: int) -> Path:
    ensure_user_space(user_id)
    return user_dir(user_id) / "PROFILE.md"


@router.get("/me/profile-md", response_model=ApiResponse[UserProfileMdOut])
def get_my_profile_md_api(current_user: User = Depends(get_current_user)):
    path = _profile_md_path(int(current_user.id))
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    return ApiResponse(data=UserProfileMdOut(content=content))


@router.put("/me/profile-md", response_model=ApiResponse[UserProfileMdOut])
def update_my_profile_md_api(
    payload: UserProfileMdOut,
    current_user: User = Depends(get_current_user),
):
    path = _profile_md_path(int(current_user.id))
    path.write_text(payload.content or "", encoding="utf-8")
    return ApiResponse(data=UserProfileMdOut(content=payload.content or ""))
