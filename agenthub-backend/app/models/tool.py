from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class Tool(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
