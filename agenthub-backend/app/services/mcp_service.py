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


def get_mcp(db: Session, mcp_id: int) -> MCP | None:
    return db.query(MCP).filter(MCP.id == mcp_id).first()


def update_mcp(db: Session, mcp_id: int, payload: dict) -> MCP:
    item = get_mcp(db, mcp_id)
    if not item:
        raise ValueError("MCP not found")
    for k, v in payload.items():
        setattr(item, k, v)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_mcp(db: Session, mcp_id: int) -> None:
    item = get_mcp(db, mcp_id)
    if not item:
        return
    db.delete(item)
    db.commit()
