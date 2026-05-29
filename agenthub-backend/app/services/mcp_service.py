from sqlalchemy.orm import Session

from app.models.mcp import MCP


def list_mcps(db: Session) -> list[MCP]:
    return db.query(MCP).order_by(MCP.id.asc()).all()


def create_mcp(db: Session, payload: dict) -> MCP:
    item = MCP(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
