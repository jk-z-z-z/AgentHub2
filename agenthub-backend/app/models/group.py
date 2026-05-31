from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class Group(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "groups"

    # Group names are not unique (DingTalk-like); use id as stable identity.
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20), default="project", nullable=False, index=True)
