from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agent_runtime.message_store import create_pending_ai_message, update_message
from app.bootstrap_runtime.engine.base import BootstrapEngineContext
from app.bootstrap_runtime.engine.factory import create_bootstrap_engine
from app.bootstrap_runtime.bootstrapbuilder import build_complete_bootstrap
from app.bootstrap_runtime.schemas import BootstrapInvokeResult
from app.bootstrap_runtime.trace import BootstrapRuntimeTrace


def _build_reply_metadata(*, reply_to_message_id: int, trigger: str, status: str) -> str:
    return json.dumps(
        {
            "reply_to": str(int(reply_to_message_id)),
            "trigger": str(trigger),
            "status": str(status),
        },
        ensure_ascii=False,
    )


async def invoke_bootstrap(
    db: Session,
    *,
    group_id: int,
    sender_member_id: int,
    user_message_id: int,
    content: str,
    meta_json: str,
    short_term_memory: list[dict[str, Any]] | list[Any],
    extra_context: dict[str, Any],
    trace_message_id: int | None = None,
) -> BootstrapInvokeResult:
    try:
        built = build_complete_bootstrap(
            db,
            group_id=int(group_id),
            sender_member_id=int(sender_member_id),
            user_message_id=int(user_message_id),
            content=str(content or ""),
            meta_json=str(meta_json or "{}"),
            short_term_memory=short_term_memory,
            extra_context=extra_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if built is None:
        return BootstrapInvokeResult(status="skipped", meta={"reason": "bootstrap_context_missing"})

    trace = BootstrapRuntimeTrace(db, message_id=trace_message_id)
    trace.emit_bootstrap_started(
        {
            "group_id": int(built.group.id),
            "agent_id": int(built.agent.id),
            "user_id": int(built.user_id),
            "user_message_id": int(user_message_id),
        },
    )
    ai_message = await create_pending_ai_message(
        db,
        group_id=int(built.group.id),
        sender_member_id=int(built.agent_member.id),
        reply_to_message_id=int(user_message_id),
        trigger="bootstrap",
    )
    try:
        engine = create_bootstrap_engine(str(built.engine_type or "agentscope_react"))
        request = type(
            "_BootstrapRunRequest",
            (),
            {
                "system_prompt": built.system_prompt,
                "short_term_memory": built.short_term_memory,
                "input_text": str(built.runtime_context.get("input_text") or ""),
                "toolkit": built.toolkit,
                "trace": trace,
            },
        )
        text, meta = await engine.run(
            ctx=BootstrapEngineContext(
                agent_id=int(built.agent.id),
                engine_type=str(built.engine_type or "agentscope_react"),
            ),
            req=request,
        )
        metadata_json = _build_reply_metadata(
            reply_to_message_id=int(user_message_id),
            trigger="bootstrap",
            status="done",
        )
        updated = await update_message(
            db,
            message_id=int(ai_message.id),
            content=str(text or ""),
            meta_json=metadata_json,
        )
        trace.emit_bootstrap_finished(
            {
                "group_id": int(built.group.id),
                "agent_id": int(built.agent.id),
                "message_id": int(updated.id),
                "status": "done",
            }
        )
        return BootstrapInvokeResult(
            text=str(text or ""),
            status="done",
            engine_type=str(meta.get("engine") or built.engine_type or ""),
            meta=dict(meta or {}),
            system_prompt_used=str(built.system_prompt or ""),
            ai_message_id=int(updated.id),
        )
    except Exception as exc:
        trace.emit_bootstrap_failed(
            {
                "group_id": int(built.group.id),
                "agent_id": int(built.agent.id),
                "message_id": int(ai_message.id),
                "error": str(exc),
            }
        )
        metadata_json = _build_reply_metadata(
            reply_to_message_id=int(user_message_id),
            trigger="bootstrap",
            status="failed",
        )
        await update_message(
            db,
            message_id=int(ai_message.id),
            content="初始化失败，请稍后重试。",
            meta_json=metadata_json,
        )
        raise
