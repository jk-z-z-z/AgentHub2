from sqlalchemy.orm import Session

from app.models.group import Group


def list_groups(db: Session) -> list[Group]:
    return db.query(Group).order_by(Group.id.asc()).all()


def create_group(db: Session, name: str, description: str | None) -> Group:
    item = Group(name=name, description=description)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
