from __future__ import annotations

from sqlalchemy.orm import Session

from app.agent_runtime.acp.provider_specs import default_acp_provider_specs
from app.models.acp_provider import ACPProvider


def ensure_default_acp_providers_seeded(db: Session, *, creator_user_id: int) -> None:
    for spec in default_acp_provider_specs():
        provider_type = str(spec["provider_type"])
        exists = (
            db.query(ACPProvider)
            .filter(ACPProvider.creator_user_id == int(creator_user_id))
            .filter(ACPProvider.provider_type == provider_type)
            .first()
        )
        if exists:
            continue
        row = ACPProvider(**spec)
        row.creator_user_id = int(creator_user_id)
        db.add(row)
    db.commit()


def list_acp_providers(db: Session, *, creator_user_id: int) -> list[ACPProvider]:
    return (
        db.query(ACPProvider)
        .filter(ACPProvider.creator_user_id == int(creator_user_id))
        .order_by(ACPProvider.id.asc())
        .all()
    )


def set_acp_provider_active(
    db: Session,
    *,
    creator_user_id: int,
    provider_type: str,
    is_active: int,
) -> ACPProvider:
    row = (
        db.query(ACPProvider)
        .filter(ACPProvider.creator_user_id == int(creator_user_id))
        .filter(ACPProvider.provider_type == str(provider_type))
        .first()
    )
    if not row:
        raise ValueError("ACP provider not found")
    row.is_active = int(is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

