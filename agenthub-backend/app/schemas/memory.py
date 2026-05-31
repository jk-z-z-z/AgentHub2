from app.schemas.common import ORMBaseModel


class ProjectMemoryCompressorStatusOut(ORMBaseModel):
    project_id: int
    last_message_id: int
    pending_message_count: int
    pending_tokens: int
    trigger_tokens: int
    keep_recent_messages: int
    will_trigger: bool
    state_file: str
    memory_file: str


class ProjectMemoryCompressRunOut(ORMBaseModel):
    compressed: bool
    reason: str | None = None
    compressed_count: int | None = None
    last_message_id: int | None = None

