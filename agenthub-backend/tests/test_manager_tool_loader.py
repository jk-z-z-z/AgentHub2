from __future__ import annotations

import asyncio

from agentscope.permission import PermissionBehavior, PermissionContext, PermissionEngine, PermissionMode

from app.manager_runtime.tool._loader import _TracedManagerTool, _build_manager_tool_groups


class _FakeTool:
    description = "fake manager tool"

    async def __call__(self, **kwargs):  # type: ignore[no-untyped-def]
        return kwargs


def test_traced_manager_tool_uses_api_safe_name() -> None:
    wrapped = _TracedManagerTool(code="manager.project_md", tool=_FakeTool())
    assert wrapped.name == "manager_project_md"
    assert wrapped._code == "manager.project_md"


def test_build_manager_tool_groups_match_internal_codes() -> None:
    wrapped = _TracedManagerTool(code="manager.project_md", tool=_FakeTool())
    groups = _build_manager_tool_groups([wrapped])

    assert len(groups) == 1
    assert groups[0].name == "context"
    assert [tool.name for tool in groups[0].tools] == ["manager_project_md"]


def test_traced_manager_tool_check_permissions_returns_passthrough_decision() -> None:
    wrapped = _TracedManagerTool(code="manager.project_md", tool=_FakeTool())
    engine = PermissionEngine(PermissionContext(mode=PermissionMode.BYPASS))

    decision = asyncio.run(engine.check_permission(wrapped, {}))

    assert decision.behavior == PermissionBehavior.ALLOW
