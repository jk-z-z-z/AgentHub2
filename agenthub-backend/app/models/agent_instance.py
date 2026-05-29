from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class AgentInstance(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "agent_instances"
    __table_args__ = (
        UniqueConstraint("group_id", "display_name", name="uq_agent_instance_group_display_name"),
        Index("idx_agent_instances_group_id", "group_id"),
        Index("idx_agent_instances_profile_id", "profile_id"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(String(255))
    api_key_ref: Mapped[str | None] = mapped_column(String(255))
    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
