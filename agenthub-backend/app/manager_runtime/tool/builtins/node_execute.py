from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.agent_runtime import invoke_agent
from app.agent_runtime.tool._executor import execute_builtin_tool
from app.manager_runtime.tool.base import build_error_chunk, build_tool_chunk
from app.models.member import Member
from app.services._zero_deps_ai_helpers import build_project_system_prompt
from app.services.group_task.dag_service import get_node
from app.services.group_task.node_status_service import complete_node


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
        node = get_node(self._db, node_id=int(node_id))
        if not node:
            return build_error_chunk("node_not_found")
        member = self._db.query(Member).filter(Member.id == int(member_id)).first()
        if not member or not member.agent_instance_id:
            return build_error_chunk("agent_member_not_found")
        agent_id = int(member.agent_instance_id)
        system_prompt = build_project_system_prompt(agent_id=agent_id, project_id=int(node.group_id))
        prompt = (
            f"你负责执行任务节点。\n"
            f"node_key={node.node_key}\n"
            f"title={node.title}\n"
            f"detail={node.detail}\n"
            "请输出结果 JSON，包含 summary、status、deliverables、evidence、confidence、issues、suggested_ops。"
        )

        def _tool_exec(tool_code: str, args: dict) -> dict:
            return execute_builtin_tool(
                agent_id=int(agent_id),
                tool_code=tool_code,
                args=args or {},
                runtime_context={"group_id": int(node.group_id), "node_id": int(node.id)},
            )

        result = await invoke_agent(
            self._db,
            agent_id=int(agent_id),
            short_term_memory=[],
            extra_context={"group_id": int(node.group_id), "node_id": int(node.id), "input_text": prompt},
            system_prompt=system_prompt,
            tool_executor=_tool_exec,
        )
        completed = complete_node(
            self._db,
            node_id=int(node.id),
            member_id=int(member.id),
            output_summary=result.text or "节点执行完成",
        )
        return build_tool_chunk(
            {
                "node_id": int(completed.id),
                "node_key": completed.node_key,
                "status": completed.status,
                "output_summary": completed.output_summary,
            }
        )
