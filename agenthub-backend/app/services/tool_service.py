from sqlalchemy.orm import Session

from app.models.tool import Tool


def list_tools(db: Session) -> list[Tool]:
    return db.query(Tool).order_by(Tool.id.asc()).all()

