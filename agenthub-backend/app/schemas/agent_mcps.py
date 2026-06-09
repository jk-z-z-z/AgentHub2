from pydantic import Field

from app.schemas.common import ORMBaseModel


class AgentMcpTogglesOut(ORMBaseModel):
    enabled: dict[str, bool] = Field(default_factory=dict, description="server_code -> enabled")


class AgentMcpTogglesUpdateRequest(ORMBaseModel):
    enabled: dict[str, bool] = Field(default_factory=dict, description="server_code -> enabled")
