from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SnowflakeMixin, TimestampMixin


class AgentProfileACPBinding(SnowflakeMixin, TimestampMixin, Base):
    __tablename__ = "agent_profile_acp_bindings"
    __table_args__ = (
        UniqueConstraint("agent_profile_id", "acp_provider_id", name="uq_agent_profile_acp_binding"),
    )

    agent_profile_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id"), nullable=False)
    acp_provider_id: Mapped[int] = mapped_column(ForeignKey("acp_providers.id"), nullable=False)
    is_primary: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
