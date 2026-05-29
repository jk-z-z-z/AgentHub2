from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class SkillCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=120)
    description: str | None = None
    content: str = Field(min_length=1)
    version: str = Field(default="1.0.0", min_length=1, max_length=50)
    is_active: int = 1


class SkillOut(ORMBaseModel):
    id: int
    name: str
    code: str
    description: str | None
    content: str
    version: str
    is_active: int
    created_at: datetime
    updated_at: datetime
