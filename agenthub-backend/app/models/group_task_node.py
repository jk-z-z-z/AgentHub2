from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class GroupTaskNode(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "group_task_nodes"
    __table_args__ = (
        Index("idx_group_task_nodes_run_id", "run_id"),
        Index("idx_group_task_nodes_status", "status"),
        Index("idx_group_task_nodes_assignee_member_id", "assignee_member_id"),
    )

    run_id: Mapped[int] = mapped_column(ForeignKey("group_task_runs.id"), nullable=False)
    node_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    role_required: Mapped[str | None] = mapped_column(String(120))
    deps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    assignee_kind: Mapped[str] = mapped_column(String(16), default="unclaimed", nullable=False)
    assignee_member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    attempt: Mapped[int] = mapped_column(default=0, nullable=False)
    input_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    receipt_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    agent_run_id: Mapped[int | None] = mapped_column(ForeignKey("agent_runs.id"))
    output_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    manager_review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
