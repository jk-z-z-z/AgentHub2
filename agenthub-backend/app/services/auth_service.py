from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import User
from app.models.user import User


def ensure_default_admin(db: Session) -> None:
    existing = db.query(User).filter(User.email == "admin@example.com").first()
    if existing:
        return
    user = User(
        email="admin@example.com",
        username="admin",
        display_name="管理员",
        password="admin123456",
        role="admin",
        status="active",
    )
    db.add(user)
    db.commit()


def login(db: Session, email: str, password: str) -> tuple[str, type[User]]:
    user = db.query(User).filter(User.email == email, User.status == "active").first()
    if not user or user.password != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(str(user.id))
    return token, user
