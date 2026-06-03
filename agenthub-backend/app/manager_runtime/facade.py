from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.manager_runtime.engine.factory import create_engine
from app.manager_runtime.managerbuilder._builder import build_complete_manager
from app.manager_runtime.schemas import ManagerInvokeResult
from app.manager_runtime.trace import ManagerRuntimeTrace


class _StrictManagerRunRequest:
    def __init__(
        self,
        *,
        group_id: int,
        input_text: str,
        system_prompt: str,
        runtime_context: dict[str, Any],
        short_term_memory: list[dict[str, Any]],
        toolkit: Any,
        trace: Any,
    ):
        self.group_id = group_id
        self.input_text = input_text
        self.system_prompt = system_prompt
        self.runtime_context = runtime_context
        self.short_term_memory = short_term_memory
        self.toolkit = toolkit
        self.trace = trace


def _normalize_short_term_memory(short_term_memory: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in short_term_memory or []:
        if isinstance(item, dict):
            normalized.append(
                {
                    "role": str(item.get("role", "user")),
                    "content": item.get("content", ""),
                    "name": item.get("name"),
                }
            )
            continue
        role = str(getattr(item, "role", "user"))
        content = getattr(item, "content", "")
        name = getattr(item, "name", None)
        normalized.append({"role": role, "content": content, "name": name})
    return normalized


def _trace_message_id(extra_context: dict[str, Any], explicit: int | None) -> int | None:
    if explicit is not None:
        return int(explicit)
    maybe = extra_context.get("trace_message_id")
    try:
        return int(maybe) if maybe not in (None, "") else None
    except (TypeError, ValueError):
        return None


async def invoke_manager(
    db: Session,
    *,
    group_id: int,
    short_term_memory: list[dict[str, Any]],
    extra_context: dict[str, Any],
    trace_message_id: int | None = None,
) -> ManagerInvokeResult:
    runtime_context = dict(extra_context or {})
    trace = ManagerRuntimeTrace(db=db, message_id=_trace_message_id(runtime_context, trace_message_id))
    built = build_complete_manager(
        db,
        group_id=int(group_id),
        short_term_memory=_normalize_short_term_memory(short_term_memory),
        extra_context={**runtime_context, "trace": trace},
    )

    input_text = str(runtime_context.get("input_text") or runtime_context.get("goal_text") or "")
    req = _StrictManagerRunRequest(
        group_id=int(group_id),
        input_text=input_text,
        system_prompt=built.system_prompt,
        runtime_context=built.runtime_context,
        short_term_memory=_normalize_short_term_memory(short_term_memory),
        toolkit=built.toolkit,
        trace=trace,
    )

    engine = create_engine(built.engine_ctx.engine_type)
    trace.emit(
        "run.started",
        {
            "group_id": int(group_id),
            "engine_type": built.engine_ctx.engine_type,
            "has_toolkit": bool(getattr(built, "toolkit", None)),
        },
    )
    try:
        text, meta = await engine.run(ctx=built.engine_ctx, req=req, tool_executor=None)
        trace.emit("run.finished", {"status": "succeeded", "engine_type": built.engine_ctx.engine_type})
        return ManagerInvokeResult(
            text=text,
            action="assistant",
            engine_type=built.engine_ctx.engine_type,
            plan={},
            meta=meta | {"group_id": int(group_id)},
            system_prompt_used=req.system_prompt,
        )
    except Exception as exc:
        trace.emit("error", {"error": str(exc), "engine_type": built.engine_ctx.engine_type})
        trace.emit("run.finished", {"status": "failed", "engine_type": built.engine_ctx.engine_type})
        raise
