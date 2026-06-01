from __future__ import annotations

import json

from agentscope.credential import OpenAICredential
from agentscope.message import TextBlock, ToolResultState
from agentscope.skill import LocalSkillLoader
from agentscope.tool import ToolBase, Toolkit, ToolChunk

from app.db.session import SessionLocal
from app.models.tool import Tool
from app.services.agent_tool_service import get_agent_tool_toggles_for_runtime
from app.services.skill_runtime_service import get_skill_loader_specs_for_agent
from app.agent_runtime.tools.executor import execute_builtin_tool


def _chunk_from_result(result: dict, ok: bool = True) -> ToolChunk:
    return ToolChunk(
        content=[TextBlock(text=json.dumps(result, ensure_ascii=False))],
        state=ToolResultState.SUCCESS if ok else ToolResultState.ERROR,
    )


def _safe_schema(schema_json: str | None) -> dict:
    try:
        schema = json.loads(schema_json or "{}")
        if isinstance(schema, dict) and schema.get("type") == "object" and isinstance(schema.get("properties"), dict):
            return schema
    except Exception:
        pass
    return {"type": "object", "properties": {}, "required": []}


class BuiltinWorkspaceTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(
        self,
        *,
        agent_id: int,
        code: str,
        description: str | None,
        schema_json: str | None,
        runtime_context: dict | None = None,
    ) -> None:
        self._agent_id = int(agent_id)
        self._code = str(code)
        self._runtime_context = runtime_context or {}
        self.name = str(code)
        self.description = description or f"Builtin tool: {code}"
        self.input_schema = _safe_schema(schema_json)
        self.is_read_only = self._code in {"file_list", "file_read", "web_search"}

    async def check_permissions(self, _tool_input: dict, _context) -> object:
        # Permission checks are enforced in execute_builtin_tool.
        return object()

    async def __call__(self, **kwargs) -> ToolChunk:
        try:
            result = execute_builtin_tool(
                agent_id=self._agent_id,
                tool_code=self._code,
                args=kwargs or {},
                runtime_context=self._runtime_context,
            )
            return _chunk_from_result(result, ok=True)
        except Exception as e:
            return _chunk_from_result({"error": str(e)}, ok=False)


def build_toolkit_for_agent(agent_instance_id: int | None, runtime_context: dict | None = None) -> Toolkit:
    if not agent_instance_id:
        return Toolkit(tools=[])

    db = SessionLocal()
    try:
        enabled = get_agent_tool_toggles_for_runtime(db, agent_id=int(agent_instance_id))
        builtins = (
            db.query(Tool)
            .filter(Tool.source_type == "builtin", Tool.is_active == 1)
            .order_by(Tool.id.asc())
            .all()
        )
    finally:
        db.close()

    tools: list[ToolBase] = []
    for item in builtins:
        if not bool(enabled.get(str(item.code), False)):
            continue
        tools.append(
            BuiltinWorkspaceTool(
                agent_id=int(agent_instance_id),
                code=str(item.code),
                description=item.description,
                schema_json=item.schema_json,
                runtime_context=runtime_context,
            )
        )
    skill_loaders = [
        LocalSkillLoader(directory=directory, scan_subdir=scan_subdir)
        for directory, scan_subdir in get_skill_loader_specs_for_agent(int(agent_instance_id))
    ]
    return Toolkit(tools=tools, skills_or_loaders=skill_loaders)
