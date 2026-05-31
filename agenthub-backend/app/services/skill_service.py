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


def get_skill(db: Session, skill_id: int) -> Skill | None:
    return db.query(Skill).filter(Skill.id == skill_id).first()


def update_skill(db: Session, skill_id: int, payload: dict) -> Skill:
    item = get_skill(db, skill_id)
    if not item:
        raise ValueError("Skill not found")
    for k, v in payload.items():
        setattr(item, k, v)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_skill(db: Session, skill_id: int) -> None:
    item = get_skill(db, skill_id)
    if not item:
        return
    db.delete(item)
    db.commit()
