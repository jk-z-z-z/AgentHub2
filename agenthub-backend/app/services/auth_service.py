from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import User
from app.models.user import User
from app.services.storage_init_service import ensure_user_space


def _init_user_space_if_possible(user_id: int) -> None:
    try:
        ensure_user_space(user_id)
    except OSError:
        # User creation should still succeed even if local storage bootstrap is unavailable.
        return


def ensure_default_admin(db: Session) -> None:
    existing = db.query(User).filter(User.email == "admin@example.com").first()
    if existing:
        return
    user = User(
        id=1,
        email="admin@example.com",
        username="admin",
        display_name="管理员",
        password="admin123456",
        role="admin",
        status="active",
    )
    db.add(user)
    db.commit()


def create_user_account(
    db: Session,
    *,
    email: str,
    username: str,
    password: str,
    display_name: str | None = None,
    role: str = "user",
    status_value: str = "active",
    bio: str | None = "",
) -> User:
    clean_email = email.strip()
    clean_username = username.strip()
    clean_display_name = display_name.strip() if display_name else None
    clean_bio = (bio or "").strip()

    if not clean_email or not clean_username or not password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email/username/password required")

    exists = db.query(User).filter((User.email == clean_email) | (User.username == clean_username)).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email or username already exists")

    row = User(
        email=clean_email,
        username=clean_username,
        password=password,
        display_name=clean_display_name,
        status=status_value,
        bio=clean_bio,
        role=role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _init_user_space_if_possible(int(row.id))
    return row


def register(db: Session, *, email: str, username: str, password: str, display_name: str | None = None, bio: str | None = "") -> tuple[str, User]:
    user = create_user_account(
        db,
        email=email,
        username=username,
        password=password,
        display_name=display_name,
        role="user",
        status_value="active",
        bio=bio,
    )
    token = create_access_token(str(user.id))
    return token, user


def login(db: Session, email: str, password: str) -> tuple[str, User]:
    user = db.query(User).filter(User.email == email, User.status == "active").first()
    if not user or user.password != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(str(user.id))
    return token, user
