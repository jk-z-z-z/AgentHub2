from __future__ import annotations

from typing import Any

from agentscope.skill import LocalSkillLoader
from agentscope.tool import ToolBase, ToolChunk, ToolGroup, Toolkit
from sqlalchemy.orm import Session

from app.event_runtime.types import MessageEventType
from app.manager_runtime.skill._loader import load_manager_skill_loaders
from app.manager_runtime.tool.base import build_error_chunk, extract_tool_result, permission_passthrough_decision
from app.manager_runtime.tool._registry import get_manager_tool_factories
def load_manager_tools(db: Session) -> dict[str, ToolBase]:
    tools: dict[str, ToolBase] = {}
    for code, factory in get_manager_tool_factories().items():
        tools[code] = factory(db)
    return tools


def _build_manager_tool_groups(tools: list[ToolBase]) -> list[ToolGroup]:
    by_code = {
        str(getattr(tool, "_code", getattr(tool, "name", ""))).strip(): tool
        for tool in tools
    }
    groups: list[ToolGroup] = []

    def add_group(name: str, description: str, instructions: str, codes: list[str]) -> None:
        selected = [by_code[code] for code in codes if code in by_code]
        if not selected:
            return
        groups.append(
            ToolGroup(
                name=name,
                description=description,
                instructions=instructions,
                tools=selected,
            )
        )

    add_group(
        "context",
        "Context and state tools.",
        "Inspect project memory, docs, and pending state before mutating anything. Do not execute nodes here.",
        ["manager.project_md", "manager.pending_state"],
    )
    add_group(
        "planning",
        "Planning tools.",
        "Use graph tools to convert requirements into an editable node graph before any execution request.",
        ["manager.dag_apply"],
    )
    add_group(
        "dag",
        "DAG view/edit tools.",
        "Use these tools to inspect or patch the task graph structure. They do not execute tasks or change node runtime state.",
        ["manager.dag_view", "manager.dag_patch"],
    )
    add_group(
        "node",
        "Node lifecycle tools.",
        "Use these tools to claim, assign, request execution, requeue, and complete nodes. Execution is event-driven: node_execute writes an event, dispatcher runs the child agent, and manager review decides final state. After node_execute succeeds, treat that node as queued/running in the background and continue planning or reply to the user; do not wait in the same turn for the child agent to finish.",
        ["manager.node_claim", "manager.node_assign_agent", "manager.node_execute", "manager.node_requeue", "manager.node_complete"],
    )
    return groups


class _TracedManagerTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(
        self,
        *,
        code: str,
        tool: object,
        trace: Any | None = None,
    ) -> None:
        self.name = str(code).strip() or "manager.tool"
        self._code = str(code)
        self._tool = tool
        self._trace = trace
        self.description = getattr(tool, "description", None) or f"Manager tool: {code}"
        self.input_schema = {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict[str, Any], _context: Any) -> Any:
        return permission_passthrough_decision()

    async def __call__(self, **kwargs: Any) -> ToolChunk:
        if self._trace:
            try:
                self._trace.emit(MessageEventType.Execution.TOOL_CALL, {"tool_code": self._code, "args": kwargs or {}})
            except Exception:
                pass
        try:
            result = await self._tool(**kwargs)
            payload = extract_tool_result(result)
            if self._trace:
                try:
                    self._trace.emit(MessageEventType.Execution.TOOL_RESULT, {"tool_code": self._code, **payload})
                except Exception:
                    pass
            return result
        except Exception as exc:
            if self._trace:
                try:
                    self._trace.emit(MessageEventType.Execution.TOOL_RESULT, {"tool_code": self._code, "error": str(exc)})
                except Exception:
                    pass
            return build_error_chunk(str(exc))


def load_manager_toolkit(
    db: Session,
    *,
    group_id: int,
    runtime_context: dict[str, Any] | None = None,
    trace: Any | None = None,
    extra_skill_loaders: list[LocalSkillLoader] | None = None,
) -> Toolkit:
    tools: list[ToolBase] = []
    for code, factory in get_manager_tool_factories().items():
        tool = factory(db)
        if runtime_context is not None and hasattr(tool, "set_runtime_context"):
            try:
                tool.set_runtime_context(runtime_context)
            except Exception:
                pass
        if trace is not None and hasattr(tool, "set_trace"):
            try:
                tool.set_trace(trace)
            except Exception:
                pass
        tools.append(_TracedManagerTool(code=code, tool=tool, trace=trace))
    skill_loaders = load_manager_skill_loaders(int(group_id))
    combined_skill_loaders = list(skill_loaders) + list(extra_skill_loaders or [])
    return Toolkit(
        skills_or_loaders=combined_skill_loaders,
        tool_groups=_build_manager_tool_groups(tools),
    )
