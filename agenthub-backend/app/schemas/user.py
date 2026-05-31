from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class UserLoginRequest(ORMBaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


class UserOut(ORMBaseModel):
    id: str
    email: str
    username: str
    display_name: str | None
    role: str
    status: str
    bio: str | None
    created_at: datetime
    updated_at: datetime


class LoginOut(ORMBaseModel):
    access_token: str
    user: UserOut

class UserCreateRequest(ORMBaseModel):
    email: str
    username: str
    display_name: str | None
    password: str
    role: str
    status: str
    bio: str


class UserSelfUpdateRequest(ORMBaseModel):
    display_name: str | None = None
    bio: str | None = None


class UserProfileMdOut(ORMBaseModel):
    content: str
