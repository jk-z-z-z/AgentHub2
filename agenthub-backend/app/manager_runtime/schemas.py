from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ManagerInvokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: int = Field(..., description="群聊/项目ID")
    short_term_memory: list[dict[str, Any]] = Field(default_factory=list, description="短期对话历史消息列表")
    extra_context: dict[str, Any] = Field(default_factory=dict, description="附加上下文")
    trace_message_id: int | None = Field(default=None, description="过程事件绑定的消息ID")


class ManagerInvokeResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: str = Field("", description="管家生成的最终回复文本")
    action: str = Field("chat", description="本次执行动作：chat/plan")
    engine_type: str = Field("manager_runtime", description="执行引擎标识")
    plan: dict[str, Any] = Field(default_factory=dict, description="规划模式下生成的DAG计划")
    meta: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    system_prompt_used: str = Field("", description="本次执行实际使用的System Prompt")
