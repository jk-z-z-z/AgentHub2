from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class GroupTaskRun(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "group_task_runs"
    __table_args__ = (
        Index("idx_group_task_runs_group_id", "group_id"),
        Index("idx_group_task_runs_status", "status"),
        Index("idx_group_task_runs_creator_member_id", "creator_member_id"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    creator_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    trigger_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
