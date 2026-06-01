from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.member import Member
from app.models.message import Message
from app.agent_runtime.internal_llm import internal_llm_chat
from app.services.storage_init_service import ensure_project_space
from app.services.storage_paths import project_dir
from app.services.token_estimator import estimate_tokens


def _state_path(project_id: int) -> Path:
    return project_dir(project_id) / "memory" / "compressor.state.json"


def _config_path(project_id: int) -> Path:
    return project_dir(project_id) / "memory" / "compressor.config.json"


def _memory_md_path(project_id: int) -> Path:
    return project_dir(project_id) / "MEMORY.md"


def _load_state(project_id: int) -> dict:
    p = _state_path(project_id)
    if not p.exists():
        return {"last_message_id": 0, "updated_at": None}
    try:
        return json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {"last_message_id": 0, "updated_at": None}


def _save_state(project_id: int, state: dict) -> None:
    p = _state_path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_config() -> dict:
    return {
        "enabled": True,
        "trigger_tokens": int(settings.memory_compress_trigger_tokens),
        "keep_recent_messages": int(settings.memory_compress_keep_recent_messages),
        "min_interval_seconds": 60,
    }


def get_project_memory_compressor_config(project_id: int) -> dict:
    ensure_project_space(project_id)
    p = _config_path(project_id)
    if not p.exists():
        cfg = _default_config()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return cfg
    try:
        raw = json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        raw = {}
    base = _default_config()
    merged = {
        "enabled": bool(raw.get("enabled", base["enabled"])),
        "trigger_tokens": max(200, int(raw.get("trigger_tokens", base["trigger_tokens"]))),
        "keep_recent_messages": max(0, int(raw.get("keep_recent_messages", base["keep_recent_messages"]))),
        "min_interval_seconds": max(0, int(raw.get("min_interval_seconds", base["min_interval_seconds"]))),
    }
    return merged


def update_project_memory_compressor_config(project_id: int, config: dict) -> dict:
    ensure_project_space(project_id)
    normalized = {
        "enabled": bool(config.get("enabled", True)),
        "trigger_tokens": max(200, int(config.get("trigger_tokens", settings.memory_compress_trigger_tokens))),
        "keep_recent_messages": max(0, int(config.get("keep_recent_messages", settings.memory_compress_keep_recent_messages))),
        "min_interval_seconds": max(0, int(config.get("min_interval_seconds", 60))),
    }
    p = _config_path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def _append_memory(project_id: int, text: str) -> None:
    p = _memory_md_path(project_id)
    existing = p.read_text(encoding="utf-8") if p.exists() else ""
    sep = "\n\n" if existing.strip() else ""
    p.write_text(f"{existing.rstrip()}{sep}{text.strip()}\n", encoding="utf-8")


def should_compress_by_tokens(messages: list[dict]) -> bool:
    # Keep compatibility for legacy callsites.
    total = 0
    for m in messages:
        total += estimate_tokens(str(m.get("content") or ""))
    return total >= int(settings.memory_compress_trigger_tokens)


def select_messages_to_compress(messages: list[dict], *, keep_recent_messages: int) -> list[dict]:
    """
    Keep the most recent N messages uncompressed.
    """
    keep = max(0, int(keep_recent_messages))
    if keep <= 0:
        return list(messages)
    if len(messages) <= keep:
        return []
    return list(messages[:-keep])


def mark_compressed(project_id: int, *, last_message_id: int) -> None:
    state = {"last_message_id": int(last_message_id), "updated_at": datetime.now(timezone.utc).isoformat()}
    _save_state(project_id, state)


def get_last_compressed_message_id(project_id: int) -> int:
    state = _load_state(project_id)
    try:
        return int(state.get("last_message_id") or 0)
    except Exception:
        return 0


def persist_project_memory_summary(project_id: int, *, summary_md: str, last_message_id: int) -> None:
    ensure_project_space(project_id)
    _append_memory(
        project_id,
        "\n".join(
            [
                f"## Memory Update ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')})",
                summary_md.strip(),
                "",
            ]
        ).strip(),
    )
    mark_compressed(project_id, last_message_id=int(last_message_id))


def get_project_memory_compressor_status(db: Session, *, project_id: int) -> dict:
    ensure_project_space(project_id)
    cfg = get_project_memory_compressor_config(int(project_id))
    last_message_id = get_last_compressed_message_id(project_id)
    all_messages = (
        db.query(Message)
        .filter(Message.group_id == int(project_id))
        .order_by(Message.id.asc())
        .all()
    )
    pending_raw = [m for m in all_messages if int(m.id) > int(last_message_id)]
    pending_items = [{"id": int(m.id), "content": str(m.content or "")} for m in pending_raw]
    pending_tokens = sum(estimate_tokens(item["content"]) for item in pending_items)
    return {
        "project_id": int(project_id),
        "last_message_id": int(last_message_id),
        "pending_message_count": len(pending_items),
        "pending_tokens": int(pending_tokens),
        "trigger_tokens": int(cfg["trigger_tokens"]),
        "keep_recent_messages": int(cfg["keep_recent_messages"]),
        "will_trigger": bool(pending_tokens >= int(cfg["trigger_tokens"])),
        "state_file": _state_path(project_id).as_posix(),
        "memory_file": _memory_md_path(project_id).as_posix(),
    }


def _query_uncompressed_messages(db: Session, *, project_id: int, last_message_id: int) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.group_id == int(project_id), Message.id > int(last_message_id))
        .order_by(Message.id.asc())
        .all()
    )


def _build_message_dicts(db: Session, *, messages: list[Message]) -> list[dict]:
    out: list[dict] = []
    for item in messages:
        member = db.query(Member).filter(Member.id == int(item.sender_member_id)).first()
        sender_kind = str(member.kind) if member else "unknown"
        sender_name = str(member.display_name) if member else str(item.sender_member_id)
        out.append(
            {
                "id": int(item.id),
                "role": "assistant" if str(item.message_type) == "ai" else "user",
                "sender_kind": sender_kind,
                "sender_name": sender_name,
                "content": str(item.content or ""),
            }
        )
    return out


def _build_summary_input(messages: list[dict]) -> str:
    lines: list[str] = []
    for item in messages:
        lines.append(
            f"[{item['id']}] ({item['role']}/{item['sender_kind']}) {item['sender_name']}: {item['content']}"
        )
    return "\n".join(lines)


async def maybe_compress_project_memory(
    db: Session,
    *,
    project_id: int,
    agent_id: int,
) -> dict:
    """
    Token-based incremental compressor:
    - reads uncompressed project messages after `compressor.state.json`
    - triggers compression once token estimate crosses threshold
    - keeps recent N messages uncompressed
    - writes compressed summary into `projects/{project_id}/MEMORY.md`
    """
    ensure_project_space(project_id)
    cfg = get_project_memory_compressor_config(int(project_id))
    if not bool(cfg.get("enabled", True)):
        return {"compressed": False, "reason": "disabled"}

    interval_sec = max(0, int(cfg.get("min_interval_seconds", 60)))
    if interval_sec > 0:
        state = _load_state(int(project_id))
        updated_at = str(state.get("updated_at") or "").strip()
        if updated_at:
            try:
                last_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                delta = (datetime.now(timezone.utc) - last_at).total_seconds()
                if delta < interval_sec:
                    return {"compressed": False, "reason": "min_interval"}
            except Exception:
                pass

    last_message_id = get_last_compressed_message_id(project_id)
    raw_messages = _query_uncompressed_messages(db, project_id=int(project_id), last_message_id=int(last_message_id))
    if not raw_messages:
        return {"compressed": False, "reason": "no_new_messages"}

    items = _build_message_dicts(db, messages=raw_messages)
    token_total = sum(estimate_tokens(str(m.get("content") or "")) for m in items)
    if token_total < int(cfg["trigger_tokens"]):
        return {"compressed": False, "reason": "below_token_threshold"}

    targets = select_messages_to_compress(items, keep_recent_messages=int(cfg["keep_recent_messages"]))
    if not targets:
        return {"compressed": False, "reason": "keep_recent_window"}

    summary_input = _build_summary_input(targets)
    summary_prompt = (
        "你是记忆压缩器。请把以下历史对话压缩为项目长期记忆（Markdown）。\n"
        "要求：\n"
        "1) 仅保留对后续协作有价值的信息；\n"
        "2) 输出结构固定为：\n"
        "## 技术决策\n## 需求与约束\n## 待办事项\n## 风险与问题\n"
        "3) 去掉寒暄和重复信息；\n"
        "4) 每条尽量简短具体。\n\n"
        f"历史对话：\n{summary_input}"
    )
    summary_md = await internal_llm_chat(
        summary_prompt,
        system_prompt="You are a precise memory compression assistant.",
        agent_instance_id=int(agent_id),
        runtime_context={"group_type": "project", "group_id": int(project_id)},
        short_term_messages=[],
    )
    if not str(summary_md or "").strip():
        return {"compressed": False, "reason": "empty_summary"}

    persist_project_memory_summary(
        int(project_id),
        summary_md=str(summary_md),
        last_message_id=int(targets[-1]["id"]),
    )
    return {
        "compressed": True,
        "compressed_count": len(targets),
        "last_message_id": int(targets[-1]["id"]),
    }
