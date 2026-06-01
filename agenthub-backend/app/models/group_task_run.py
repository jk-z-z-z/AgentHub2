from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class GroupTaskRun(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "group_task_runs"
    __table_args__ = (
        Index("idx_group_task_runs_group_id", "group_id"),
        Index("idx_group_task_runs_status", "status"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    creator_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    trigger_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planning", nullable=False)
    dag_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    runtime_dir: Mapped[str] = mapped_column(String(500), nullable=False)
    final_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
