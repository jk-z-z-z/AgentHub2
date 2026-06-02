from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class AgentInstance(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "agent_instances"

    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(String(255))
    api_key_ref: Mapped[str | None] = mapped_column(String(255))
    engine_type: Mapped[str] = mapped_column(String(40), default="internal_llm", nullable=False)
    engine_config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
