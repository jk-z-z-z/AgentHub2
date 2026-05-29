from datetime import datetime

from pydantic import Field

from app.schemas.common import ORMBaseModel


class ACPProviderCreateRequest(ORMBaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider_type: str = Field(min_length=1, max_length=80)
    transport_type: str = Field(min_length=1, max_length=50)
    endpoint: str | None = Field(default=None, max_length=255)
    capability_json: str = "{}"
    auth_config_json: str = "{}"
    is_active: int = 1


class ACPProviderOut(ORMBaseModel):
    id: int
    name: str
    provider_type: str
    transport_type: str
    endpoint: str | None
    capability_json: str
    auth_config_json: str
    is_active: int
    created_at: datetime
    updated_at: datetime
