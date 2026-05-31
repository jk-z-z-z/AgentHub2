from pydantic import Field

from app.schemas.common import ORMBaseModel


class AIChatRequest(ORMBaseModel):
    message: str = Field(min_length=1)
    system_prompt: str | None = None
    agent_instance_id: str | None = None
    runtime_context: dict | None = None


class AIChatResponse(ORMBaseModel):
    reply: str
