from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.storage_paths import project_dir


def _runs_dir(group_id: int) -> Path:
    root = project_dir(int(group_id))
    p = root / "runs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pending_plan_path(group_id: int) -> Path:
    return _runs_dir(int(group_id)) / "pending_plan.json"


def _pending_clarify_path(group_id: int) -> Path:
    return _runs_dir(int(group_id)) / "pending_clarify.json"


def save_pending_plan(*, group_id: int, creator_member_id: int, plan: dict) -> None:
    path = _pending_plan_path(int(group_id))
    now = datetime.now(timezone.utc)
    payload = {
        "group_id": int(group_id),
        "creator_member_id": int(creator_member_id),
        "plan": plan,
        "created_at": now.isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_pending_plan(*, group_id: int) -> dict | None:
    path = _pending_plan_path(int(group_id))
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def clear_pending_plan(*, group_id: int) -> None:
    path = _pending_plan_path(int(group_id))
    if path.exists():
        path.unlink()


def save_pending_clarify(*, group_id: int, creator_member_id: int, goal_text: str, questions: list[str]) -> None:
    path = _pending_clarify_path(int(group_id))
    now = datetime.now(timezone.utc)
    payload = {
        "group_id": int(group_id),
        "creator_member_id": int(creator_member_id),
        "goal_text": str(goal_text or ""),
        "questions": list(questions or []),
        "created_at": now.isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_pending_clarify(*, group_id: int) -> dict | None:
    path = _pending_clarify_path(int(group_id))
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def clear_pending_clarify(*, group_id: int) -> None:
    path = _pending_clarify_path(int(group_id))
    if path.exists():
        path.unlink()
