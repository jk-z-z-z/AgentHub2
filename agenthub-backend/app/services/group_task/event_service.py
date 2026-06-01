from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.group_task_event import GroupTaskEvent
from app.models.group_task_run import GroupTaskRun


def _next_seq(db: Session, *, run_id: int) -> int:
    latest = (
        db.query(GroupTaskEvent)
        .filter(GroupTaskEvent.run_id == int(run_id))
        .order_by(GroupTaskEvent.seq.desc())
        .first()
    )
    return int(latest.seq) + 1 if latest else 1


def _append_event_file(run: GroupTaskRun, event: GroupTaskEvent) -> None:
    root = Path(run.runtime_dir) / "events"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "events.jsonl"
    entry = {
        "id": int(event.id),
        "run_id": int(event.run_id),
        "node_id": int(event.node_id) if event.node_id else None,
        "seq": int(getattr(event, "seq", 0) or 0),
        "event_type": event.event_type,
        "payload": json.loads(event.payload_json or "{}"),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_group_task_events(db: Session, *, run_id: int) -> list[GroupTaskEvent]:
    return (
        db.query(GroupTaskEvent)
        .filter(GroupTaskEvent.run_id == int(run_id))
        .order_by(GroupTaskEvent.id.asc())
        .all()
    )


def log_group_task_event(
    db: Session,
    *,
    run_id: int,
    node_id: int | None,
    event_type: str,
    payload: dict | None = None,
    run: GroupTaskRun | None = None,
) -> GroupTaskEvent:
    target_run = run
    if target_run is None:
        target_run = db.query(GroupTaskRun).filter(GroupTaskRun.id == int(run_id)).first()
    if not target_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    event = GroupTaskEvent(
        run_id=int(run_id),
        node_id=int(node_id) if node_id is not None else None,
        seq=_next_seq(db, run_id=int(run_id)),
        event_type=str(event_type),
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    _append_event_file(target_run, event)
    return event
