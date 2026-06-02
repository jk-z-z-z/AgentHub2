from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AutoIncrementIdMixin, Base, TimestampMixin


class MCP(AutoIncrementIdMixin, TimestampMixin, Base):
    __tablename__ = "mcps"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    server_code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    connection_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    capability_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
