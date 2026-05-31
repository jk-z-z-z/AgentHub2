from app.schemas.common import ORMBaseModel


class ProjectMemoryCompressorConfigOut(ORMBaseModel):
    enabled: bool
    trigger_tokens: int
    keep_recent_messages: int
    min_interval_seconds: int


class ProjectMemoryCompressorConfigUpdateRequest(ORMBaseModel):
    enabled: bool
    trigger_tokens: int
    keep_recent_messages: int
    min_interval_seconds: int

