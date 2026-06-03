from __future__ import annotations

from typing import Any

from agentscope.skill import LocalSkillLoader
from agentscope.tool import ToolBase, ToolGroup, Toolkit

from app.bootstrap_runtime.skill import load_bootstrap_skill_loaders
from app.bootstrap_runtime.tool._builtins_init import get_bootstrap_tools


def _build_tool_groups(tools: list[ToolBase]) -> list[ToolGroup]:
    by_code = {str(getattr(tool, "name", "")).strip(): tool for tool in tools}
    groups: list[ToolGroup] = []

    def add_group(name: str, description: str, instructions: str, codes: list[str]) -> None:
        selected = [by_code[code] for code in codes if code in by_code]
        if selected:
            groups.append(ToolGroup(name=name, description=description, instructions=instructions, tools=selected))

    add_group(
        "workspace",
        "Bootstrap workspace files.",
        "Use these tools to inspect and update the agent workspace.",
        ["bootstrap.file_list", "bootstrap.file_read", "bootstrap.file_write", "bootstrap.file_delete"],
    )
    return groups


def load_bootstrap_toolkit(
    agent_id: int,
    *,
    runtime_context: dict[str, Any] | None = None,
    trace: Any | None = None,
    extra_skill_loaders: list[LocalSkillLoader] | None = None,
) -> Toolkit:
    tools = [tool for tool in get_bootstrap_tools()]
    skill_loaders = load_bootstrap_skill_loaders()
    combined_skill_loaders = list(skill_loaders) + list(extra_skill_loaders or [])
    return Toolkit(
        skills_or_loaders=combined_skill_loaders,
        tools=tools,
        tool_groups=_build_tool_groups(tools),
    )
