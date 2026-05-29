from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class GroupCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class GroupOut(ORMBaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
