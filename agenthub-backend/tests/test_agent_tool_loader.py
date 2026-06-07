from __future__ import annotations

import asyncio
import json

from agentscope.message import ToolResultState

from app.agent_runtime.tool._loader import BuiltinAgentTool


def test_builtin_agent_tool_uses_custom_executor() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def fake_executor(tool_code: str, args: dict[str, str]) -> dict[str, str]:
        calls.append((tool_code, args))
        return {"ok": "yes"}

    tool = BuiltinAgentTool(
        agent_id=1,
        code="project_code_write",
        description="write project file",
        schema_json=json.dumps(
            {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
            ensure_ascii=False,
        ),
        runtime_context={"group_type": "project", "group_id": 100},
        tool_executor=fake_executor,
    )

    chunk = asyncio.run(tool(path="pages/login.html", content="<h1>login</h1>"))

    assert calls == [("project_code_write", {"path": "pages/login.html", "content": "<h1>login</h1>"})]
    assert chunk.state == ToolResultState.SUCCESS
    assert chunk.content[0].text == '{"ok": "yes"}'
