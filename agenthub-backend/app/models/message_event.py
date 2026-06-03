from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class MessageEvent(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "message_events"
    __table_args__ = (
        Index("idx_message_events_message_id", "message_id"),
        Index("idx_message_events_message_seq", "message_id", "seq"),
        Index("idx_message_events_category", "category"),
        Index("idx_message_events_status", "status"),
    )

    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="system", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
