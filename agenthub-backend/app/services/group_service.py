from sqlalchemy.orm import Session
import time

from sqlalchemy.exc import IntegrityError

from app.models.group import Group
from app.models.member import Member
from app.models.message import Message
from app.services.storage_paths import project_dir
from app.services.storage_init_service import ensure_personal_group_space, ensure_project_space


def list_groups(db: Session, *, user_id: int | None = None) -> list[Group]:
    query = db.query(Group)
    if user_id is not None:
        query = (
            query.join(Member, Member.group_id == Group.id)
            .filter(Member.kind == "user", Member.user_ref == str(user_id))
        )
    return query.order_by(Group.id.asc()).all()


def create_group(
    db: Session,
    name: str,
    description: str | None,
    *,
    creator_user_id: int,
    group_type: str = "project",
) -> Group:
    item = Group(
        creator_user_id=int(creator_user_id),
        name=name,
        description=description,
        type=group_type,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        # Backward compatible with old sqlite schema where groups.name was UNIQUE.
        db.rollback()
        # Ensure a deterministic unique suffix for retries.
        item = Group(
            creator_user_id=int(creator_user_id),
            name=f"{name} ({time.time_ns()})",
            description=description,
            type=group_type,
        )
        db.add(item)
        db.commit()
    db.refresh(item)
    # init dirs after id generated
    if group_type in {"personal", "bootstrap"}:
        ensure_personal_group_space(int(item.id))
    else:
        ensure_project_space(int(item.id))
        from app.services.workspace_runtime_service import ensure_workspace_for_group

        ensure_workspace_for_group(db, group=item)
    return item


def get_group(db: Session, group_id: int) -> Group | None:
    return db.query(Group).filter(Group.id == group_id).first()


def delete_group(db: Session, *, group_id: int) -> None:
    """
    Delete a group and its related rows.
    Order matters:
      messages -> members -> group
    """
    # Delete messages first (sender_member_id references members)
    db.query(Message).filter(Message.group_id == group_id).delete(synchronize_session=False)
    db.query(Member).filter(Member.group_id == group_id).delete(synchronize_session=False)
    db.query(Group).filter(Group.id == group_id).delete(synchronize_session=False)
    db.commit()

    # Best-effort remove project storage for this group_id.
    try:
        p = project_dir(group_id)
        if p.exists() and p.is_dir():
            # Only remove within this directory; ignore errors.
            for child in sorted(p.rglob("*"), reverse=True):
                try:
                    if child.is_file() or child.is_symlink():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                except Exception:
                    pass
            try:
                p.rmdir()
            except Exception:
                pass
    except Exception:
        pass
