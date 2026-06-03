from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agentscope.message import TextBlock, ToolResultState
from agentscope.skill import LocalSkillLoader
from agentscope.tool import ToolBase, ToolGroup, Toolkit, ToolChunk

from app.event_runtime.types import MessageEventType
from ._builtins_init import BUILTIN_TOOL_DEFS
from app.agent_runtime.skill._loader import load_skill_loaders_for_agent
from app.services.storage_paths import agent_dir


class _TracedBuiltinTool(ToolBase):
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
        runtime_context: dict[str, Any] | None = None,
        trace: Any | None = None,
    ):
        self._agent_id = int(agent_id)
        self._code = str(code)
        self._runtime_context = runtime_context or {}
        self._trace = trace
        self.name = str(code)
        self.description = description or f"Builtin tool: {code}"
        self.input_schema = self._safe_schema(schema_json)
        self._call_traces: list[dict[str, Any]] = []

    @staticmethod
    def _safe_schema(schema_json: str | None) -> dict[str, Any]:
        try:
            schema = json.loads(schema_json or "{}")
            if isinstance(schema, dict) and schema.get("type") == "object" and isinstance(schema.get("properties"), dict):
                return schema
        except Exception:
            pass
        return {"type": "object", "properties": {}, "required": []}

    async def check_permissions(self, _tool_input: dict[str, Any], _context: Any) -> Any:
        return object()

    async def __call__(self, **kwargs: Any) -> ToolChunk:
        start_time = time.perf_counter()
        if self._trace:
            try:
                self._trace.emit(MessageEventType.Execution.TOOL_CALL, {"tool_code": self._code, "args": kwargs or {}})
            except Exception:
                pass
        trace_record: dict[str, Any] = {
            "tool_code": self._code,
            "agent_id": self._agent_id,
            "args": kwargs,
            "timestamp": time.time(),
        }
        try:
            from app.agent_runtime.tool._executor import execute_builtin_tool

            result = execute_builtin_tool(
                agent_id=self._agent_id,
                tool_code=self._code,
                args=kwargs or {},
                runtime_context=self._runtime_context,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            trace_record.update({"status": "success", "duration_ms": duration_ms, "result_preview": str(result)[:200]})
            self._call_traces.append(trace_record)
            if self._trace:
                try:
                    self._trace.emit(MessageEventType.Execution.TOOL_RESULT, {"tool_code": self._code, "result": result})
                except Exception:
                    pass
            return ToolChunk(
                content=[TextBlock(text=json.dumps(result, ensure_ascii=False))],
                state=ToolResultState.SUCCESS,
            )
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            trace_record.update({"status": "failed", "duration_ms": duration_ms, "error": str(e)})
            self._call_traces.append(trace_record)
            if self._trace:
                try:
                    self._trace.emit(MessageEventType.Execution.TOOL_RESULT, {"tool_code": self._code, "error": str(e)})
                except Exception:
                    pass
            return ToolChunk(
                content=[TextBlock(text=json.dumps({"error": str(e)}, ensure_ascii=False))],
                state=ToolResultState.ERROR,
            )


def _get_tools_json_path(agent_id: int) -> Path:
    root = agent_dir(agent_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / "tools.json"


def _normalize_toggles(enabled: dict[str, bool], allowed_codes: list[str]) -> dict[str, bool]:
    normalized = {code: True for code in allowed_codes}
    for k, v in (enabled or {}).items():
        key = str(k)
        if key in normalized:
            normalized[key] = bool(v)
    return normalized


def _build_tool_groups(tools: list[ToolBase]) -> list[ToolGroup]:
    by_code = {str(getattr(tool, "name", "")).strip(): tool for tool in tools}
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
        "workspace",
        "Workspace file operations.",
        "Always inspect before editing and keep changes minimal.",
        ["file_list", "file_read", "file_write", "file_edit"],
    )
    add_group(
        "project",
        "Project shared code and commands.",
        "Prefer project-scoped reads and safe allowlisted commands.",
        ["project_code_list", "project_code_read", "project_command_run"],
    )
    add_group(
        "runtime",
        "Runtime workspace file operations.",
        "Use runtime-scoped files when the task belongs to current execution context.",
        ["worker_file_list", "worker_file_read", "worker_file_write"],
    )
    add_group(
        "profile",
        "Agent and user profile maintenance.",
        "Keep profile updates structured and section-based when possible.",
        ["user_profile_write", "agent_spec_write", "agent_spec_delete", "agent_profile_upsert_section"],
    )
    return groups


def load_toolkit_for_agent(
    agent_id: int,
    runtime_context: dict[str, Any] | None = None,
    trace: Any | None = None,
    extra_skill_loaders: list[LocalSkillLoader] | None = None,
) -> Toolkit:
    allowed_codes = [str(k) for k in sorted(BUILTIN_TOOL_DEFS.keys())]
    tools_json_path = _get_tools_json_path(int(agent_id))

    stored_enabled: dict[str, bool] = {}
    if tools_json_path.exists():
        try:
            raw = json.loads(tools_json_path.read_text(encoding="utf-8") or "{}")
            if isinstance(raw, dict) and isinstance(raw.get("enabled"), dict):
                stored_enabled = {str(k): bool(v) for k, v in raw.get("enabled", {}).items()}
        except Exception:
            pass

    normalized_enabled = _normalize_toggles(stored_enabled, allowed_codes)
    tools: list[ToolBase] = []
    for code in allowed_codes:
        if not bool(normalized_enabled.get(code, True)):
            continue
        spec = BUILTIN_TOOL_DEFS.get(code)
        if not spec:
            continue
        tools.append(
            _TracedBuiltinTool(
                agent_id=int(agent_id),
                code=str(code),
                description=spec.spec.get("description"),
                schema_json=json.dumps(spec.spec.get("input_schema", {}), ensure_ascii=False),
                runtime_context=runtime_context,
                trace=trace,
            )
        )
    skill_loaders = load_skill_loaders_for_agent(int(agent_id))
    combined_skill_loaders = list(skill_loaders) + list(extra_skill_loaders or [])
    return Toolkit(
        skills_or_loaders=combined_skill_loaders,
        tools=tools,
        tool_groups=_build_tool_groups(tools),
    )
