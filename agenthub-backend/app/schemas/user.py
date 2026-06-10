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
    email: str = Field(min_length=3, max_length=255)
    username: str = Field(min_length=2, max_length=120)
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=6, max_length=255)
    role: str = Field(default="user", min_length=1, max_length=50)
    status: str = Field(default="active", min_length=1, max_length=20)
    bio: str = Field(default="", max_length=2000)


class UserRegisterRequest(ORMBaseModel):
    email: str = Field(min_length=3, max_length=255)
    username: str = Field(min_length=2, max_length=120)
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=6, max_length=255)
    bio: str = Field(default="", max_length=2000)


class UserSelfUpdateRequest(ORMBaseModel):
    display_name: str | None = None
    bio: str | None = None


class UserProfileMdOut(ORMBaseModel):
    content: str
