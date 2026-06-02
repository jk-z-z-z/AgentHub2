from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agent_runtime import invoke_agent
from app.agent_runtime.message_store import create_pending_ai_message, update_message
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
    trace.emit(
        "bootstrap.start",
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
        trigger="bootstrap_auto",
    )
    try:
        result = await invoke_agent(
            db,
            agent_id=int(built.agent.id),
            short_term_memory=built.short_term_memory,
            extra_context=built.runtime_context,
            system_prompt=built.system_prompt,
            trace_message_id=int(ai_message.id),
        )
        metadata_json = _build_reply_metadata(
            reply_to_message_id=int(user_message_id),
            trigger="bootstrap_auto",
            status="done",
        )
        updated = await update_message(
            db,
            message_id=int(ai_message.id),
            content=str(result.text or ""),
            meta_json=metadata_json,
        )
        trace.emit(
            "bootstrap.finish",
            {
                "group_id": int(built.group.id),
                "agent_id": int(built.agent.id),
                "message_id": int(updated.id),
                "status": "done",
            },
        )
        return BootstrapInvokeResult(
            text=str(result.text or ""),
            status="done",
            engine_type=str(result.engine_type or ""),
            meta=dict(result.meta or {}),
            system_prompt_used=str(result.system_prompt_used or ""),
            ai_message_id=int(updated.id),
        )
    except Exception as exc:
        trace.emit(
            "bootstrap.error",
            {
                "group_id": int(built.group.id),
                "agent_id": int(built.agent.id),
                "message_id": int(ai_message.id),
                "error": str(exc),
            },
        )
        metadata_json = _build_reply_metadata(
            reply_to_message_id=int(user_message_id),
            trigger="bootstrap_auto",
            status="failed",
        )
        await update_message(
            db,
            message_id=int(ai_message.id),
            content="初始化失败，请稍后重试。",
            meta_json=metadata_json,
        )
        raise
