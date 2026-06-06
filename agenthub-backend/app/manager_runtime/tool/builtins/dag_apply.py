from __future__ import annotations

from agentscope.tool import ToolBase, ToolChunk
from sqlalchemy.orm import Session

from app.manager_runtime.tool.base import ManagerRuntimeContextMixin, build_error_chunk, build_tool_chunk
from app.services.group_task_service import create_run, list_nodes, replace_run_nodes, resolve_run


class DagApplyTool(ManagerRuntimeContextMixin, ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db: Session) -> None:
        self._db = db
        self.set_runtime_context(None)
        self.name = "manager.dag_apply"
        self.description = (
            "Replace the DAG for a task run with a structured graph. "
            "If run_id is omitted, create a new run from the current conversation context."
        )
        self.input_schema = {
            "type": "object",
            "properties": {
                "run_id": {"type": "integer"},
                "group_id": {"type": "integer"},
                "creator_member_id": {"type": "integer"},
                "trigger_message_id": {"type": "integer"},
                "title": {"type": "string"},
                "goal_text": {"type": "string"},
                "graph": {"type": "object"},
            },
            "additionalProperties": True,
        }

    async def check_permissions(self, _tool_input: dict, _context: object) -> object:
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        graph = dict(kwargs.get("graph") or {})
        nodes = list(graph.get("nodes") or kwargs.get("nodes") or [])
        if not nodes:
            return build_error_chunk("graph_nodes_required")

        run_id = self._resolve_run_id(kwargs.get("run_id"))
        if run_id is not None:
            run = resolve_run(self._db, run_id=int(run_id))
            current = list_nodes(self._db, run_id=int(run_id))
            action = "updated" if current else "created"
            replace_run_nodes(self._db, run_id=int(run_id), nodes=nodes)
            return build_tool_chunk(
                {
                    "action": action,
                    "group_id": int(run.group_id),
                    "run_id": int(run.id),
                    "node_count": len(nodes),
                }
            )

        group_id = self._resolve_group_id(kwargs.get("group_id"))
        creator_member_id = self._resolve_creator_member_id(kwargs.get("creator_member_id"))
        if group_id is None or creator_member_id is None:
            return build_error_chunk("group_or_creator_context_missing")

        title = self._default_title(kwargs.get("title") or graph.get("title"))
        goal_text = self._default_goal_text(kwargs.get("goal_text") or graph.get("goal_text") or graph.get("goal"))
        trigger_message_id = self._resolve_trigger_message_id(kwargs.get("trigger_message_id"))
        run = create_run(
            self._db,
            group_id=int(group_id),
            creator_member_id=int(creator_member_id),
            title=title,
            goal_text=goal_text,
            nodes=nodes,
            trigger_message_id=trigger_message_id,
        )
        return build_tool_chunk(
            {
                "action": "created",
                "group_id": int(run.group_id),
                "run_id": int(run.id),
                "node_count": len(nodes),
                "title": str(run.title or ""),
                "goal_text": str(run.goal_text or ""),
            }
        )
