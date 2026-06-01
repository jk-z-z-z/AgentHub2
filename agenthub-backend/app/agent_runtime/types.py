from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentRunRequest:
    agent_id: int
    input_text: str
    system_prompt: str | None = None
    runtime_context: dict | None = None
    short_term_messages: list[object] | None = None


@dataclass
class AgentRunResult:
    text: str
    engine_type: str
    meta: dict

