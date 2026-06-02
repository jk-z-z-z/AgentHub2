from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.manager_runtime.engine.base import ManagerEngineContext
from app.models.group import Group
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
    extra = dict(extra_context or {})
    run_preview = ""
    run_id = extra.get("group_task_run_id") or extra.get("task_run_id")
    if run_id not in (None, ""):
        run_root = root / "runs" / str(run_id)
        dag_text = _read_text(run_root / "dag.json")[:3000]
        run_text = _read_text(run_root / "run.json")[:3000]
        run_preview = "\n".join([p for p in [dag_text, run_text] if p])

    return {
        "group_id": int(group_id),
        "group_name": str(group.name or f"group-{int(group_id)}") if group else f"group-{int(group_id)}",
        "group_type": str(group.type or "project") if group else "project",
        "project_root": root.as_posix(),
        "memory_preview": _read_text(root / "MEMORY.md")[:6000],
        "profile_preview": _read_text(root / "PROFILE.md")[:4000],
        "readme_preview": _read_text(root / "README.md")[:4000],
        "docs_preview": _load_docs_preview(root),
        "run_preview": run_preview,
        "short_term_preview": _short_term_preview(short_term_memory),
    }


def build_manager_system_prompt(
    *,
    context: dict[str, Any],
    purpose: str,
    extra_context: dict[str, Any] | None = None,
) -> str:
    extra = dict(extra_context or {})
    purpose = str(purpose or "chat").strip().lower()
    goal_text = str(extra.get("goal_text") or extra.get("input_text") or "").strip()
    clarify_answers = str(extra.get("clarify_answers") or "").strip()
    prompt_parts = [
        "你是群聊项目的管家（Master），负责答疑、规划、必要时组织节点执行。",
        "你只服务当前群聊项目，不要脱离群聊上下文回答。",
        f"当前项目目录：{context['project_root']}",
        f"当前群组名称：{context['group_name']}",
        f"当前群组类型：{context['group_type']}",
    ]
    if str(context.get("profile_preview") or "").strip():
        prompt_parts.append(f"管家资料摘要：\n{str(context.get('profile_preview') or '')[:4000]}")
    if str(context.get("memory_preview") or "").strip():
        prompt_parts.append(f"项目长期记忆摘要：\n{str(context.get('memory_preview') or '')[:6000]}")
    if str(context.get("readme_preview") or "").strip():
        prompt_parts.append(f"项目说明摘要：\n{str(context.get('readme_preview') or '')[:4000]}")
    docs_preview = context.get("docs_preview") or []
    if isinstance(docs_preview, list) and docs_preview:
        docs_text = "\n".join([f"- {item.get('path')}: {item.get('preview')}" for item in docs_preview if isinstance(item, dict)])
        prompt_parts.append(f"项目文档预览：\n{docs_text[:4000]}")
    if str(context.get("run_preview") or "").strip():
        prompt_parts.append(f"当前任务运行摘要：\n{str(context.get('run_preview') or '')[:4000]}")
    if str(context.get("short_term_preview") or "").strip():
        prompt_parts.append(f"短期对话摘要：\n{str(context.get('short_term_preview') or '')[:2000]}")

    if purpose == "plan":
        prompt_parts.append("当前任务是生成DAG规划草案。你必须只输出合法JSON对象，不要markdown，不要解释。")
        prompt_parts.append(
            "JSON schema: {\"plan_title\":\"string\",\"goal\":\"string\",\"nodes\":[{\"node_key\":\"N1\",\"title\":\"string\",\"detail\":\"string\",\"role_required\":\"string|null\",\"deps\":[\"N0\"]}]}"
        )
        if goal_text:
            prompt_parts.append(f"用户目标：\n{goal_text}")
        if clarify_answers:
            prompt_parts.append(f"用户补充回答：\n{clarify_answers}")
    else:
        prompt_parts.append(
            "当前任务是正常对话。你可以回答问题、解释项目上下文、建议下一步；如果用户明确要求规划，再切换到规划思维。"
        )
        if goal_text:
            prompt_parts.append(f"用户当前输入：\n{goal_text}")

    return "\n\n".join(prompt_parts).strip()


@dataclass
class BuiltManager:
    group: Group | None
    system_prompt: str
    runtime_context: dict[str, Any]
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
    runtime_context = dict(context)
    runtime_context["purpose"] = str(extra_context.get("purpose") or "chat")
    engine_ctx = ManagerEngineContext(
        group_id=int(group_id),
        engine_type="internal_llm",
        engine_config_json="{}",
    )
    return BuiltManager(
        group=group,
        system_prompt=system_prompt,
        runtime_context=runtime_context,
        engine_ctx=engine_ctx,
    )
