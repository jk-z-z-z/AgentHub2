from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.event_runtime.facade import list_group_message_event_feed
from app.memory_runtime.token_estimator import estimate_tokens
from app.services.storage_init_service import ensure_project_space
from app.services.storage_paths import project_dir


def _state_path(project_id: int) -> Path:
    return project_dir(project_id) / "memory" / "compressor.state.json"


def _config_path(project_id: int) -> Path:
    return project_dir(project_id) / "memory" / "compressor.config.json"


def _memory_md_path(project_id: int) -> Path:
    return project_dir(project_id) / "MEMORY.md"


def _load_state(project_id: int) -> dict:
    path = _state_path(project_id)
    if not path.exists():
        return {"last_message_id": 0, "updated_at": None}
    try:
        return json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {"last_message_id": 0, "updated_at": None}


def _save_state(project_id: int, state: dict) -> None:
    path = _state_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_config() -> dict:
    return {
        "enabled": True,
        "trigger_tokens": int(settings.memory_compress_trigger_tokens),
        "keep_recent_messages": int(settings.memory_compress_keep_recent_messages),
        "min_interval_seconds": 60,
    }


def get_project_memory_compressor_config(project_id: int) -> dict:
    ensure_project_space(project_id)
    path = _config_path(project_id)
    if not path.exists():
        config = _default_config()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return config
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        raw = {}
    base = _default_config()
    return {
        "enabled": bool(raw.get("enabled", base["enabled"])),
        "trigger_tokens": max(200, int(raw.get("trigger_tokens", base["trigger_tokens"]))),
        "keep_recent_messages": max(0, int(raw.get("keep_recent_messages", base["keep_recent_messages"]))),
        "min_interval_seconds": max(0, int(raw.get("min_interval_seconds", base["min_interval_seconds"]))),
    }


def update_project_memory_compressor_config(project_id: int, config: dict) -> dict:
    ensure_project_space(project_id)
    normalized = {
        "enabled": bool(config.get("enabled", True)),
        "trigger_tokens": max(200, int(config.get("trigger_tokens", settings.memory_compress_trigger_tokens))),
        "keep_recent_messages": max(0, int(config.get("keep_recent_messages", settings.memory_compress_keep_recent_messages))),
        "min_interval_seconds": max(0, int(config.get("min_interval_seconds", 60))),
    }
    path = _config_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def _append_memory(project_id: int, text: str) -> None:
    path = _memory_md_path(project_id)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    separator = "\n\n" if existing.strip() else ""
    path.write_text(f"{existing.rstrip()}{separator}{text.strip()}\n", encoding="utf-8")


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


def _build_summary_input(messages: list[dict]) -> str:
    lines: list[str] = []
    for item in messages:
        lines.append(f"[message {item['message_id']}] role={item['role']} sender={item['sender_member_id']} type={item['message_type']}")
        for event in item["events"]:
            payload = event["payload"]
            if isinstance(payload, dict):
                payload_text = ""
                for key in ("content", "text", "reply_text", "summary"):
                    value = payload.get(key)
                    if isinstance(value, str) and value.strip():
                        payload_text = value.strip()
                        break
                if not payload_text:
                    payload_text = json.dumps(payload, ensure_ascii=False, default=str)
            else:
                payload_text = str(payload)
            lines.append(f"  - {event['event_type']}: {payload_text}")
    return "\n".join(lines)


def get_project_memory_compressor_status(db: Session, *, project_id: int) -> dict:
    ensure_project_space(project_id)
    config = get_project_memory_compressor_config(int(project_id))
    last_message_id = get_last_compressed_message_id(project_id)
    pending_items = list_group_message_event_feed(
        db,
        group_id=int(project_id),
        after_message_id=int(last_message_id),
        limit_messages=120,
    )
    pending_tokens = estimate_tokens(_build_summary_input(pending_items))
    return {
        "project_id": int(project_id),
        "last_message_id": int(last_message_id),
        "pending_message_count": len(pending_items),
        "pending_tokens": int(pending_tokens),
        "trigger_tokens": int(config["trigger_tokens"]),
        "keep_recent_messages": int(config["keep_recent_messages"]),
        "will_trigger": bool(pending_tokens >= int(config["trigger_tokens"])),
        "state_file": _state_path(project_id).as_posix(),
        "memory_file": _memory_md_path(project_id).as_posix(),
    }


def _text_content(text: Any) -> list[Any]:
    if isinstance(text, list):
        return text
    return [{"type": "text", "text": str(text or "")}]


def _message_role(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role", "user"))
    return str(getattr(message, "role", "user"))


def _message_content(message: Any) -> Any:
    if isinstance(message, dict):
        return message.get("content", "")
    return getattr(message, "content", "")


def _extract_response_text(response: Any) -> str:
    parts = getattr(response, "content", None) or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            texts.append(str(part.get("text") or ""))
        elif getattr(part, "type", None) == "text":
            texts.append(str(getattr(part, "text", "") or ""))
    return "".join(texts).strip()


async def _chat(user_prompt: str, system_prompt: str | None = None, short_term_messages: list | None = None) -> str:
    cred = OpenAICredential(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    model = OpenAIChatModel(credential=cred, model=settings.openai_model, stream=False)
    messages: list[Msg] = []
    if system_prompt:
        messages.append(Msg(role="system", content=_text_content(system_prompt), name="system"))
    for message in short_term_messages or []:
        role = _message_role(message)
        messages.append(Msg(role=role, content=_text_content(_message_content(message)), name=role))
    messages.append(Msg(role="user", content=_text_content(user_prompt), name="user"))
    response = await model(messages)
    return _extract_response_text(response)


def select_messages_to_compress(messages: list[dict], *, keep_recent_messages: int) -> list[dict]:
    keep = max(0, int(keep_recent_messages))
    if keep <= 0:
        return list(messages)
    if len(messages) <= keep:
        return []
    return list(messages[:-keep])


async def compress_project_memory(db: Session, *, project_id: int) -> dict:
    ensure_project_space(project_id)
    config = get_project_memory_compressor_config(int(project_id))
    if not bool(config.get("enabled", True)):
        return {"compressed": False, "reason": "disabled"}

    interval_sec = max(0, int(config.get("min_interval_seconds", 60)))
    if interval_sec > 0:
        state = _load_state(int(project_id))
        updated_at = str(state.get("updated_at") or "").strip()
        if updated_at:
            try:
                last_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - last_at).total_seconds() < interval_sec:
                    return {"compressed": False, "reason": "min_interval"}
            except Exception:
                pass

    last_message_id = get_last_compressed_message_id(project_id)
    feed = list_group_message_event_feed(
        db,
        group_id=int(project_id),
        after_message_id=int(last_message_id),
        limit_messages=120,
    )
    if not feed:
        return {"compressed": False, "reason": "no_new_messages"}

    token_total = estimate_tokens(_build_summary_input(feed))
    if token_total < int(config["trigger_tokens"]):
        return {"compressed": False, "reason": "below_token_threshold"}

    targets = select_messages_to_compress(feed, keep_recent_messages=int(config["keep_recent_messages"]))
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
    summary_md = await _chat(
        summary_prompt,
        system_prompt="You are a precise memory compression assistant.",
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


async def maybe_compress_project_memory(
    db: Session,
    *,
    project_id: int,
) -> dict:
    return await compress_project_memory(db, project_id=int(project_id))
