from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class Message(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_group_id", "group_id"),
        Index("idx_messages_sender_member_id", "sender_member_id"),
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    sender_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reply_to_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
