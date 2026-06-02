"""AgentRuntime 数字员工运行时包。

企业级架构重构完成版本。
本包唯一对外暴露入口：invoke_agent()

所有内部模块以下划线 _ 开头，禁止外部代码直接导入。
"""

from app.agent_runtime.facade import invoke_agent
from app.agent_runtime.schemas import AgentInvokeRequest, AgentInvokeResult

__all__ = [
    "AgentInvokeRequest",
    "AgentInvokeResult",
    "invoke_agent",
]
