from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class ToolCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=120)
    description: str | None = None
    source_type: str = Field(min_length=1, max_length=50)
    tool_schema_json: str = Field(default="{}", alias="schema_json", serialization_alias="schema_json")
    is_active: int = 1


class ToolOut(ORMBaseModel):
    id: int
    name: str
    code: str
    description: str | None
    source_type: str
    tool_schema_json: str = Field(alias="schema_json", serialization_alias="schema_json")
    is_active: int
    created_at: datetime
    updated_at: datetime
