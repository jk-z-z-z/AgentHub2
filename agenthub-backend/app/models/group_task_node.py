from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class GroupTaskNode(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "group_task_nodes"
    __table_args__ = (
        Index("idx_group_task_nodes_group_id", "group_id"),
        Index("idx_group_task_nodes_status", "status"),
        Index("idx_group_task_nodes_assignee_member_id", "assignee_member_id"),
        Index("idx_group_task_nodes_parent_node_id", "parent_node_id"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    parent_node_id: Mapped[int | None] = mapped_column(ForeignKey("group_task_nodes.id"))
    node_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    role_required: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    assignee_kind: Mapped[str] = mapped_column(String(16), default="unclaimed", nullable=False)
    assignee_member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    attempt: Mapped[int] = mapped_column(default=0, nullable=False)
    input_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    output_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
