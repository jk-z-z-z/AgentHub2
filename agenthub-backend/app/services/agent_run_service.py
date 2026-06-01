from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.models.agent_run_event import AgentRunEvent
from app.services.storage_paths import runtime_root


def _run_root(run_id: int) -> Path:
    root = runtime_root() / "runs" / str(int(run_id))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _append_jsonl(*, run: AgentRun, event: AgentRunEvent) -> None:
    root = Path(run.runtime_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "debug_history.jsonl"
    entry = {
        "event_id": int(event.id),
        "agent_run_id": int(event.agent_run_id),
        "seq": int(event.seq),
        "event_type": str(event.event_type),
        "payload": json.loads(event.payload_json or "{}"),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def create_agent_run(
    db: Session,
    *,
    group_id: int,
    agent_instance_id: int,
    trigger_message_id: int | None,
    mode: str,
    group_task_run_id: int | None = None,
    group_task_node_id: int | None = None,
) -> AgentRun:
    run = AgentRun(
        group_id=int(group_id),
        agent_instance_id=int(agent_instance_id),
        trigger_message_id=int(trigger_message_id) if trigger_message_id else None,
        group_task_run_id=int(group_task_run_id) if group_task_run_id else None,
        group_task_node_id=int(group_task_node_id) if group_task_node_id else None,
        mode=str(mode or "chat"),
        status="running",
        runtime_dir="",
        result_json="{}",
        final_message_id=None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run_dir = _run_root(int(run.id))
    run.runtime_dir = run_dir.as_posix()
    db.add(run)
    db.commit()
    db.refresh(run)
    # create meta.json for quick inspection
    try:
        meta = {
            "agent_run_id": int(run.id),
            "group_id": int(group_id),
            "agent_instance_id": int(agent_instance_id),
            "trigger_message_id": int(trigger_message_id) if trigger_message_id else None,
            "mode": run.mode,
            "group_task_run_id": int(group_task_run_id) if group_task_run_id else None,
            "group_task_node_id": int(group_task_node_id) if group_task_node_id else None,
        }
        (run_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return run


def _next_seq(db: Session, *, agent_run_id: int) -> int:
    latest = (
        db.query(AgentRunEvent)
        .filter(AgentRunEvent.agent_run_id == int(agent_run_id))
        .order_by(AgentRunEvent.seq.desc())
        .first()
    )
    return int(latest.seq) + 1 if latest else 1


def log_agent_run_event(db: Session, *, run: AgentRun, event_type: str, payload: dict | None = None) -> AgentRunEvent:
    ev = AgentRunEvent(
        agent_run_id=int(run.id),
        seq=_next_seq(db, agent_run_id=int(run.id)),
        event_type=str(event_type),
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    _append_jsonl(run=run, event=ev)
    return ev


def finalize_agent_run(
    db: Session,
    *,
    run: AgentRun,
    status: str,
    result: dict,
    final_message_id: int | None = None,
) -> AgentRun:
    run.status = str(status)
    run.result_json = json.dumps(result or {}, ensure_ascii=False)
    run.final_message_id = int(final_message_id) if final_message_id else None
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

