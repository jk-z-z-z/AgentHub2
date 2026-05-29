from sqlalchemy.orm import Session

from app.models.skill import Skill


def list_skills(db: Session) -> list[Skill]:
    return db.query(Skill).order_by(Skill.id.asc()).all()


def create_skill(db: Session, payload: dict) -> Skill:
    item = Skill(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
