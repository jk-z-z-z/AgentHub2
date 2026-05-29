from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class MessageCreateRequest(ORMBaseModel):
    group_id: str
    sender_member_id: str
    message_type: str = Field(default="text", min_length=1, max_length=50)
    content: str = Field(min_length=1)
    metadata_json: str = "{}"


class MessageOut(ORMBaseModel):
    id: str
    group_id: str
    sender_member_id: str
    message_type: str
    content: str
    metadata_json: str
    created_at: datetime
    updated_at: datetime
