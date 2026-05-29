from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class MCPCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    server_code: str = Field(min_length=1, max_length=120)
    description: str | None = None
    connection_json: str = "{}"
    capability_json: str = "{}"
    is_active: int = 1


class MCPOut(ORMBaseModel):
    id: int
    name: str
    server_code: str
    description: str | None
    connection_json: str
    capability_json: str
    is_active: int
    created_at: datetime
    updated_at: datetime
