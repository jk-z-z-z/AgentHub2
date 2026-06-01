from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agent_runtime.executor import run_agent
from app.agent_runtime.types import AgentRunRequest, AgentRunResult
from app.models.agent_run import AgentRun
from app.services.agent_run_service import create_agent_run, finalize_agent_run, log_agent_run_event


@dataclass(frozen=True)
class AgentRunExecuteResult:
    run: AgentRun
    result: AgentRunResult


async def execute_agent_run(
    db: Session,
    *,
    group_id: int,
    agent_instance_id: int,
    input_text: str,
    system_prompt: str,
    runtime_context: dict,
    short_term_messages=None,
    trigger_message_id: int | None = None,
    mode: str = "chat",
    group_task_run_id: int | None = None,
    group_task_node_id: int | None = None,
    tool_executor=None,
) -> AgentRunExecuteResult:
    run = create_agent_run(
        db,
        group_id=int(group_id),
        agent_instance_id=int(agent_instance_id),
        trigger_message_id=int(trigger_message_id) if trigger_message_id else None,
        mode=mode,
        group_task_run_id=group_task_run_id,
        group_task_node_id=group_task_node_id,
    )
    log_agent_run_event(
        db,
        run=run,
        event_type="run.started",
        payload={"mode": mode, "group_id": int(group_id), "agent_instance_id": int(agent_instance_id)},
    )

    def _wrapped_tool_exec(tool_code: str, args: dict) -> dict:
        log_agent_run_event(db, run=run, event_type="tool.call", payload={"tool": tool_code, "args": args or {}})
        out = tool_executor(tool_code, args) if tool_executor else {}
        log_agent_run_event(db, run=run, event_type="tool.result", payload={"tool": tool_code, "result": out})
        return out

    try:
        log_agent_run_event(
            db,
            run=run,
            event_type="llm.request",
            payload={"input_preview": str(input_text or "")[:500], "system_preview": str(system_prompt or "")[:300]},
        )
        result = await run_agent(
            db,
            req=AgentRunRequest(
                agent_id=int(agent_instance_id),
                input_text=input_text,
                system_prompt=system_prompt,
                runtime_context=runtime_context,
                short_term_messages=short_term_messages,  # type: ignore[arg-type]
            ),
            tool_executor=_wrapped_tool_exec if tool_executor else None,
        )
        log_agent_run_event(db, run=run, event_type="llm.response", payload={"text_preview": str(result.text or "")[:800]})
        finalize_agent_run(db, run=run, status="succeeded", result={"final_text": result.text, "engine_type": result.engine_type, "meta": result.meta})
        log_agent_run_event(db, run=run, event_type="run.finished", payload={"status": "succeeded"})
        return AgentRunExecuteResult(run=run, result=result)
    except Exception as e:
        finalize_agent_run(db, run=run, status="failed", result={"error": str(e)})
        log_agent_run_event(db, run=run, event_type="error", payload={"error": str(e)})
        log_agent_run_event(db, run=run, event_type="run.finished", payload={"status": "failed"})
        raise

