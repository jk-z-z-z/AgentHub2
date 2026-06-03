from __future__ import annotations

from typing import Any

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.common.project_prompt import build_project_system_prompt
from app.agent_runtime import invoke_agent
from app.agent_runtime.tool._executor import execute_builtin_tool
from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.models.member import Member
from app.services.group_task_service import complete_node, get_node


def _build_execution_prompt(*, node_key: str, title: str, detail: str) -> str:
    return (
        "你负责执行任务节点。\n"
        f"node_key={node_key}\n"
        f"title={title}\n"
        f"detail={detail}\n"
        "请输出结果 JSON，包含 summary、status、deliverables、evidence、confidence、issues、suggested_ops。"
    )


def _build_tool_executor(*, agent_id: int, group_id: int, node_id: int) -> Any:
    def _tool_exec(tool_code: str, args: dict) -> dict:
        return execute_builtin_tool(
            agent_id=int(agent_id),
            tool_code=str(tool_code),
            args=args or {},
            runtime_context={"group_id": int(group_id), "node_id": int(node_id)},
        )

    return _tool_exec


def _resolve_node_and_member(db: Session, *, node_id: int, member_id: int) -> tuple[Any | None, Any | None]:
    node = get_node(db, node_id=int(node_id))
    if not node:
        return None, None
    member = db.query(Member).filter(Member.id == int(member_id)).first()
    if not member or not member.agent_instance_id:
        return node, None
    return node, member


class NodeExecuteTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.name = "manager.node_execute"
        self.description = "Execute a node via the assigned agent."
        self.input_schema = {
            "type": "object",
            "properties": {
                "node_id": {"type": "integer"},
                "member_id": {"type": "integer"},
            },
            "required": ["node_id", "member_id"],
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        node_id = kwargs.get("node_id")
        member_id = kwargs.get("member_id")
        if node_id in (None, "") or member_id in (None, ""):
            return build_error_chunk("node_id_and_member_id_required")
        node, member = _resolve_node_and_member(self._db, node_id=int(node_id), member_id=int(member_id))
        if not node:
            return build_error_chunk("node_not_found")
        if not member:
            return build_error_chunk("agent_member_not_found")
        agent_id = int(member.agent_instance_id)
        system_prompt = build_project_system_prompt(agent_id=agent_id, project_id=int(node.group_id))
        prompt = _build_execution_prompt(node_key=str(node.node_key), title=str(node.title), detail=str(node.detail))

        result = await invoke_agent(
            self._db,
            agent_id=int(agent_id),
            short_term_memory=[],
            extra_context={"group_id": int(node.group_id), "node_id": int(node.id), "input_text": prompt},
            system_prompt=system_prompt,
            tool_executor=_build_tool_executor(agent_id=agent_id, group_id=int(node.group_id), node_id=int(node.id)),
        )
        completed = complete_node(
            self._db,
            node_id=int(node.id),
            member_id=int(member.id),
            output_summary=result.text or "节点执行完成",
        )
        return build_tool_chunk(_build_execute_result(completed))


def _build_execute_result(completed: Any) -> dict[str, Any]:
    return {
        "node_id": int(completed.id),
        "node_key": completed.node_key,
        "status": completed.status,
        "output_summary": completed.output_summary,
    }
