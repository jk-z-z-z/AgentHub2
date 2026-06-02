from __future__ import annotations

from typing import Callable

from sqlalchemy.orm import Session

from app.manager_runtime.tool.builtins.delegate_node import DelegateNodeTool
from app.manager_runtime.tool.builtins.project_md import ProjectMdTool
from app.manager_runtime.tool.builtins.pending_state import PendingStateTool
from app.manager_runtime.tool.builtins.plan_apply import PlanApplyTool

ToolFactory = Callable[[Session], object]


def get_manager_tool_factories() -> dict[str, ToolFactory]:
    return {
        "manager.project_md": lambda _db: ProjectMdTool(),
        "manager.delegate_node": lambda db: DelegateNodeTool(db=db),
        "manager.pending_state": lambda _db: PendingStateTool(),
        "manager.apply_plan": lambda db: PlanApplyTool(db=db),
    }
