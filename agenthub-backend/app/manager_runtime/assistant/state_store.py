from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.services.storage_paths import project_dir


def _runs_dir(group_id: int, *, create: bool = True) -> Path:
    root = project_dir(int(group_id))
    p = root / "runs"
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_context_key(context_key: str | int | None = None, trigger_message_id: int | str | None = None) -> str:
    raw = context_key if context_key not in (None, "") else trigger_message_id
    value = str(raw if raw not in (None, "") else "default").strip()
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value or "default"


def _pending_context_dir(
    group_id: int,
    *,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
    create: bool = True,
) -> Path:
    p = _runs_dir(int(group_id), create=create) / "pending" / _safe_context_key(
        context_key=context_key,
        trigger_message_id=trigger_message_id,
    )
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def _pending_plan_path(
    group_id: int,
    *,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
    create: bool = True,
) -> Path:
    return _pending_context_dir(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
        create=create,
    ) / "pending_plan.json"


def _pending_clarify_path(
    group_id: int,
    *,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
    create: bool = True,
) -> Path:
    return _pending_context_dir(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
        create=create,
    ) / "pending_clarify.json"


def _bind_pending_file_run_id(path: Path, *, run_id: int | str) -> None:
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return
    if not isinstance(payload, dict):
        return
    payload["run_id"] = int(run_id)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def bind_pending_run(
    *,
    group_id: int,
    run_id: int | str,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
) -> None:
    _bind_pending_file_run_id(
        _pending_plan_path(
            int(group_id),
            context_key=context_key,
            trigger_message_id=trigger_message_id,
            create=False,
        ),
        run_id=run_id,
    )
    _bind_pending_file_run_id(
        _pending_clarify_path(
            int(group_id),
            context_key=context_key,
            trigger_message_id=trigger_message_id,
            create=False,
        ),
        run_id=run_id,
    )


def save_pending_plan(
    *,
    group_id: int,
    creator_member_id: int,
    plan: dict,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
    run_id: int | str | None = None,
) -> None:
    path = _pending_plan_path(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
    )
    now = datetime.now(timezone.utc)
    payload = {
        "group_id": int(group_id),
        "context_key": _safe_context_key(context_key=context_key, trigger_message_id=trigger_message_id),
        "trigger_message_id": int(trigger_message_id) if trigger_message_id not in (None, "") else None,
        "run_id": int(run_id) if run_id not in (None, "") else None,
        "creator_member_id": int(creator_member_id),
        "plan": plan,
        "created_at": now.isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_pending_plan(
    *,
    group_id: int,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
) -> dict | None:
    path = _pending_plan_path(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
    )
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def clear_pending_plan(
    *,
    group_id: int,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
) -> None:
    path = _pending_plan_path(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
    )
    if path.exists():
        path.unlink()


def save_pending_clarify(
    *,
    group_id: int,
    creator_member_id: int,
    goal_text: str,
    questions: list[str],
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
    run_id: int | str | None = None,
) -> None:
    path = _pending_clarify_path(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
    )
    now = datetime.now(timezone.utc)
    payload = {
        "group_id": int(group_id),
        "context_key": _safe_context_key(context_key=context_key, trigger_message_id=trigger_message_id),
        "trigger_message_id": int(trigger_message_id) if trigger_message_id not in (None, "") else None,
        "run_id": int(run_id) if run_id not in (None, "") else None,
        "creator_member_id": int(creator_member_id),
        "goal_text": str(goal_text or ""),
        "questions": list(questions or []),
        "created_at": now.isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_pending_clarify(
    *,
    group_id: int,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
) -> dict | None:
    path = _pending_clarify_path(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
    )
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def clear_pending_clarify(
    *,
    group_id: int,
    context_key: str | int | None = None,
    trigger_message_id: int | str | None = None,
) -> None:
    path = _pending_clarify_path(
        int(group_id),
        context_key=context_key,
        trigger_message_id=trigger_message_id,
    )
    if path.exists():
        path.unlink()
