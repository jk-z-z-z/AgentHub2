from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class GroupAssistantConfig(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "group_assistant_configs"
    __table_args__ = (
        UniqueConstraint("group_id", name="uq_group_assistant_group_id"),
        Index("idx_group_assistant_group_id", "group_id"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    assistant_agent_instance_id: Mapped[int | None] = mapped_column(ForeignKey("agent_instances.id"))
    enabled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    creator_user_id: Mapped[int] = mapped_column(Integer, nullable=False)

