from sqlalchemy.orm import Session

from app.models.tool import Tool


def list_tools(db: Session) -> list[Tool]:
    return db.query(Tool).order_by(Tool.id.asc()).all()


def create_tool(db: Session, payload: dict) -> Tool:
    item = Tool(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_tool(db: Session, tool_id: int) -> Tool | None:
    return db.query(Tool).filter(Tool.id == tool_id).first()


def update_tool(db: Session, tool_id: int, payload: dict) -> Tool:
    item = get_tool(db, tool_id)
    if not item:
        raise ValueError("Tool not found")
    for k, v in payload.items():
        setattr(item, k, v)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_tool(db: Session, tool_id: int) -> None:
    item = get_tool(db, tool_id)
    if not item:
        return
    db.delete(item)
    db.commit()
