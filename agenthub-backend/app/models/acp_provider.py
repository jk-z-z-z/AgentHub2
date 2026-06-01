from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class ACPProvider(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "acp_providers"

    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(80), nullable=False)
    transport_type: Mapped[str] = mapped_column(String(50), nullable=False, default="stdio")
    endpoint: Mapped[str | None] = mapped_column(String(255))
    capability_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    auth_config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

