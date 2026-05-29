from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.common.snowflake import SnowflakeConfig, SnowflakeGenerator


snowflake = SnowflakeGenerator(SnowflakeConfig())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SnowflakeMixin:
    id: Mapped[int] = mapped_column(primary_key=True, default=snowflake.next_id)
