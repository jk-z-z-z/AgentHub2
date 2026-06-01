from __future__ import annotations

from datetime import datetime

from app.schemas.common import ORMBaseModel


class AgentRunOut(ORMBaseModel):
    id: str
    group_id: str
    agent_instance_id: str
    trigger_message_id: str | None
    group_task_run_id: str | None
    group_task_node_id: str | None
    mode: str
    status: str
    runtime_dir: str
    result_json: str
    final_message_id: str | None
    created_at: datetime
    updated_at: datetime


class AgentRunEventOut(ORMBaseModel):
    id: str
    agent_run_id: str
    seq: int
    event_type: str
    payload_json: str
    created_at: datetime
    updated_at: datetime

