from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BootstrapInvokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: int = Field(..., description="bootstrap 群聊ID")
    sender_member_id: int = Field(..., description="触发 bootstrap 的用户成员ID")
    user_message_id: int = Field(..., description="触发 bootstrap 的用户消息ID")
    content: str = Field("", description="用户输入文本")
    meta_json: str = Field("{}", description="消息元数据 JSON")
    short_term_memory: list[dict[str, Any]] = Field(default_factory=list, description="短期上下文")
    extra_context: dict[str, Any] = Field(default_factory=dict, description="附加上下文")
    trace_message_id: int | None = Field(default=None, description="用于记录过程事件的消息ID")


class BootstrapInvokeResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: str = Field("", description="Bootstrap 生成的回复文本")
    status: str = Field("done", description="执行状态")
    engine_type: str = Field("", description="实际引擎类型")
    meta: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    system_prompt_used: str = Field("", description="本次执行实际使用的完整System Prompt")
    ai_message_id: int | None = Field(default=None, description="本次 bootstrap 生成的消息ID")
