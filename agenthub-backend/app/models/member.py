from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class Member(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("group_id", "display_name", name="uq_member_group_display_name"),
        Index("idx_members_group_id", "group_id"),
        Index("idx_members_kind", "kind"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    user_ref: Mapped[str | None] = mapped_column(String(120))
    agent_instance_id: Mapped[int | None] = mapped_column(ForeignKey("agent_instances.id"))
    title: Mapped[str | None] = mapped_column(String(120))
