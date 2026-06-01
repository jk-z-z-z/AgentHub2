from __future__ import annotations

import json

from agentscope.agent import Agent
from agentscope.credential import OpenAICredential
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from agentscope.tool import ToolBase, Toolkit, ToolChunk
from agentscope.message import TextBlock, ToolResultState

from app.core.config import settings
from app.services.manager_planning_service import manager_tool_read_group_memory_context


class _ManagerReadContextTool(ToolBase):
    is_mcp = False
    is_external_tool = False
    is_state_injected = False
    is_concurrency_safe = True

    def __init__(self, *, db, group_id: int) -> None:
        self._db = db
        self._group_id = int(group_id)
        self.name = "manager.read_context"
        self.description = "Read project MEMORY.md and docs preview for planning."
        self.input_schema = {"type": "object", "properties": {}, "required": []}
        self.is_read_only = True

    async def __call__(self, **kwargs) -> ToolChunk:
        _ = kwargs
        ctx = manager_tool_read_group_memory_context(self._db, group_id=int(self._group_id))
        return ToolChunk(content=[TextBlock(text=json.dumps(ctx, ensure_ascii=False))], state=ToolResultState.SUCCESS)


async def build_plan_with_react_agent(*, db, group_id: int, goal_text: str) -> str:
    """
    Manager planning as a ReAct loop (NOT ACP).

    Returns raw model text (expected to be JSON plan).
    """
    cred = OpenAICredential(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    model = OpenAIChatModel(credential=cred, model=settings.openai_model, stream=False)
    toolkit = Toolkit(tools=[_ManagerReadContextTool(db=db, group_id=int(group_id))])
    system_prompt = (
        "你是群聊中的管家Agent，只做任务规划，不执行任务。\n"
        "你必须先调用工具 manager.read_context 获取群聊长期记忆与文档摘要，再输出规划JSON。\n"
        "禁止输出运维排障/落库失败排查类内容，必须围绕用户目标。\n"
        "必须针对具体业务域输出可执行节点，禁止输出空泛模板（需求/设计/开发/测试 这种泛化分解不能直接用）。\n"
        "输出必须是JSON对象，schema：{plan_title, goal, nodes:[{node_key,title,detail,role_required,deps}]}。\n"
        "节点数 3-8，deps 只能引用已存在 node_key。"
    )
    agent = Agent(name="group-manager", system_prompt=system_prompt, model=model, toolkit=toolkit)
    # Manager uses only internal tools and must not delegate to ACP.
    try:
        from agentscope.permission import PermissionMode

        agent.state.permission_context.mode = PermissionMode.BYPASS
    except Exception:
        pass
    user = Msg(name="user", role="user", content=[{"type": "text", "text": f"目标：{goal_text}"}])
    reply = await agent.reply([user])
    parts: list[str] = []
    for part in reply.content:
        if isinstance(part, dict) and part.get("type") == "text":
            parts.append(str(part.get("text") or ""))
    return "".join(parts).strip()
