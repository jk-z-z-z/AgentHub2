from sqlalchemy.orm import Session

from app.models.acp_provider import ACPProvider


def list_acp_providers(db: Session) -> list[ACPProvider]:
    return db.query(ACPProvider).order_by(ACPProvider.id.asc()).all()


def create_acp_provider(db: Session, payload: dict) -> ACPProvider:
    item = ACPProvider(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
