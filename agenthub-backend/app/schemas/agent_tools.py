from pydantic import Field

from app.schemas.common import ORMBaseModel


class AgentToolTogglesOut(ORMBaseModel):
    enabled: dict[str, bool] = Field(default_factory=dict, description="tool_code -> enabled")


class AgentToolTogglesUpdateRequest(ORMBaseModel):
    enabled: dict[str, bool] = Field(default_factory=dict, description="tool_code -> enabled")

