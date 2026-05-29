from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import UserOut, UserCreateRequest

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
    return ApiResponse(data=UserOut.model_validate(row))

