from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentscope.tool import Toolkit
from sqlalchemy.orm import Session

from app.manager_runtime.engine.base import ManagerEngineContext
from app.models.group import Group
from app.models.member import Member
from app.manager_runtime.skill._loader import load_manager_skill_loaders, load_manager_skill_prompt_sections
from app.manager_runtime.tool._loader import load_manager_toolkit
from app.services.storage_paths import project_dir


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def _load_docs_preview(root: Path, *, limit: int = 8) -> list[dict[str, str]]:
    docs_dir = root / "knowledge"
    items: list[dict[str, str]] = []
    if not docs_dir.exists() or not docs_dir.is_dir():
        return items
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except Exception:
            continue
        items.append({"path": rel, "preview": _read_text(path)[:220]})
        if len(items) >= limit:
            break
    return items


def _agent_members_preview(db: Session, *, group_id: int, limit: int = 8) -> list[dict[str, object]]:
    rows = (
        db.query(Member)
        .filter(Member.group_id == int(group_id), Member.kind == "agent")
        .order_by(Member.id.asc())
        .all()
    )
    items: list[dict[str, object]] = []
    for row in rows[:limit]:
        items.append(
            {
                "member_id": int(row.id),
                "display_name": str(row.display_name or ""),
                "title": str(row.title or ""),
                "agent_instance_id": int(row.agent_instance_id) if row.agent_instance_id else None,
            }
        )
    return items


def _short_term_preview(short_term_memory: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in short_term_memory[-24:]:
        if isinstance(item, dict):
            role = str(item.get("role", "user"))
            content = item.get("content", "")
        else:
            role = str(getattr(item, "role", "user"))
            content = getattr(item, "content", "")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                content = first.get("text", "")
            else:
                content = getattr(first, "text", "")
        lines.append(f"{role}: {str(content or '')}")
    return "\n".join(lines)


def build_manager_runtime_context(
    db: Session,
    *,
    group_id: int,
    short_term_memory: list[dict[str, Any]],
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    root = project_dir(int(group_id)).resolve()

    return {
        "group_id": int(group_id),
        "group_name": str(group.name or f"group-{int(group_id)}") if group else f"group-{int(group_id)}",
        "group_type": str(group.type or "project") if group else "project",
        "project_root": root.as_posix(),
        "memory_preview": _read_text(root / "MEMORY.md")[:6000],
        "profile_preview": _read_text(root / "PROFILE.md")[:4000],
        "readme_preview": _read_text(root / "README.md")[:4000],
        "docs_preview": _load_docs_preview(root),
        "agent_members_preview": _agent_members_preview(db, group_id=int(group_id)),
        "short_term_preview": _short_term_preview(short_term_memory),
        "skill_loaders": load_manager_skill_loaders(int(group_id)),
        "skill_prompt_sections": load_manager_skill_prompt_sections(int(group_id)),
    }


def build_manager_system_prompt(
    *,
    context: dict[str, Any],
    purpose: str,
    extra_context: dict[str, Any] | None = None,
) -> str:
    extra = dict(extra_context or {})
    prompt_parts = [
        "你是群聊项目的管家（Master）。",
        "你只服务当前群聊项目，使用已挂载的 skills 和 tools 完成任务。",
        f"当前项目：{context['group_name']} ({context['group_type']})",
        f"项目目录：{context['project_root']}",
        "当你调用 manager.node_execute 后，这只表示节点已经进入后台异步执行。不要在同一轮回复里等待子 agent 真正完成；应该继续安排其余节点，或直接向用户汇报“已开始执行”。",
    ]
    for label, key, limit in [
        ("项目长期记忆摘要", "memory_preview", 3000),
        ("项目说明摘要", "readme_preview", 2000),
        ("项目文档预览", "docs_preview", 3000),
        ("可分配 agent 成员", "agent_members_preview", 1200),
        ("短期对话摘要", "short_term_preview", 1200),
    ]:
        value = context.get(key)
        if not value:
            continue
        if isinstance(value, list):
            lines = []
            for item in value:
                if isinstance(item, dict):
                    if "path" in item:
                        lines.append(f"- {item.get('path')}: {item.get('preview')}")
                    elif "member_id" in item:
                        lines.append(
                            f"- member_id={item.get('member_id')}, "
                            f"display_name={item.get('display_name')}, "
                            f"title={item.get('title')}"
                        )
            text = "\n".join(lines)
        else:
            text = str(value)
        if text.strip():
            prompt_parts.append(f"{label}：\n{text[:limit]}")

    skill_sections = context.get("skill_prompt_sections")
    if isinstance(skill_sections, list) and skill_sections:
        skill_text_parts: list[str] = []
        for item in skill_sections:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            skill_text_parts.append(f"## {name}\n{content}")
        if skill_text_parts:
            prompt_parts.append("技能说明：\n" + "\n\n".join(skill_text_parts[:12]))

    if str(extra.get("goal_text") or extra.get("input_text") or "").strip():
        prompt_parts.append(f"用户输入：\n{str(extra.get('goal_text') or extra.get('input_text') or '').strip()}")
    if str(extra.get("clarify_answers") or "").strip():
        prompt_parts.append(f"补充回答：\n{str(extra.get('clarify_answers') or '').strip()}")

    return "\n\n".join(prompt_parts).strip()


@dataclass
class BuiltManager:
    group: Group | None
    system_prompt: str
    runtime_context: dict[str, Any]
    toolkit: Toolkit
    engine_ctx: ManagerEngineContext


def build_complete_manager(
    db: Session,
    *,
    group_id: int,
    short_term_memory: list[dict[str, Any]],
    extra_context: dict[str, Any],
) -> BuiltManager:
    context = build_manager_runtime_context(
        db,
        group_id=int(group_id),
        short_term_memory=short_term_memory,
        extra_context=extra_context,
    )
    system_prompt = build_manager_system_prompt(
        context=context,
        purpose=str(extra_context.get("purpose") or "chat"),
        extra_context=extra_context,
    )
    group = db.query(Group).filter(Group.id == int(group_id)).first()
    runtime_context = {**context, **dict(extra_context or {})}
    runtime_context["purpose"] = str(extra_context.get("purpose") or "chat")
    engine_ctx = ManagerEngineContext(
        group_id=int(group_id),
        engine_type=str(extra_context.get("engine_type") or "agentscope_react"),
        engine_config_json=str(extra_context.get("engine_config_json") or "{}"),
    )
    extra_skill_loaders = extra_context.get("runtime_skill_loaders")
    if not isinstance(extra_skill_loaders, list):
        extra_skill_loaders = []
    return BuiltManager(
        group=group,
        system_prompt=system_prompt,
        runtime_context=runtime_context,
        toolkit=load_manager_toolkit(
            db,
            group_id=int(group_id),
            runtime_context=runtime_context,
            trace=extra_context.get("trace"),
            extra_skill_loaders=extra_skill_loaders,
        ),
        engine_ctx=engine_ctx,
    )
