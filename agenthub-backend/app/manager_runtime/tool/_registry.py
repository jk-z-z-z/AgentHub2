from __future__ import annotations

from typing import Callable

from agentscope.tool import ToolBase
from sqlalchemy.orm import Session

from app.manager_runtime.tool.builtins.dag_patch import DagPatchTool
from app.manager_runtime.tool.builtins.dag_view import DagViewTool
from app.manager_runtime.tool.builtins.node_assign_agent import NodeAssignAgentTool
from app.manager_runtime.tool.builtins.node_claim import NodeClaimTool
from app.manager_runtime.tool.builtins.node_complete import NodeCompleteTool
from app.manager_runtime.tool.builtins.node_execute import NodeExecuteTool
from app.manager_runtime.tool.builtins.project_md import ProjectMdTool
from app.manager_runtime.tool.builtins.pending_state import PendingStateTool
from app.manager_runtime.tool.builtins.plan_apply import PlanApplyTool

ToolFactory = Callable[[Session], ToolBase]


def get_manager_tool_factories() -> dict[str, ToolFactory]:
    return {
        "manager.project_md": lambda _db: ProjectMdTool(),
        "manager.dag_patch": lambda db: DagPatchTool(db=db),
        "manager.dag_view": lambda db: DagViewTool(db=db),
        "manager.node_claim": lambda db: NodeClaimTool(db=db),
        "manager.node_complete": lambda db: NodeCompleteTool(db=db),
        "manager.node_assign_agent": lambda db: NodeAssignAgentTool(db=db),
        "manager.node_execute": lambda db: NodeExecuteTool(db=db),
        "manager.pending_state": lambda _db: PendingStateTool(),
        "manager.apply_plan": lambda db: PlanApplyTool(db=db),
    }
