from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class AgentInvokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: int = Field(..., description="数字员工实例唯一ID")
    short_term_memory: list[dict[str, Any]] = Field(default_factory=list, description="短期对话历史消息列表")
    extra_context: dict[str, Any] = Field(default_factory=dict, description="附加上下文")


class AgentInvokeResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: str = Field("", description="Agent生成的最终回复文本")
    engine_type: str = Field("", description="实际使用的引擎类型")
    meta: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    system_prompt_used: str = Field("", description="本次执行实际使用的完整System Prompt")
