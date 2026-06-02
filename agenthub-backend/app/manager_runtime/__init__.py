"""ManagerRuntime 管家运行时包。"""

from app.manager_runtime.facade import invoke_manager
from app.manager_runtime.schemas import ManagerInvokeRequest, ManagerInvokeResult

__all__ = [
    "ManagerInvokeRequest",
    "ManagerInvokeResult",
    "invoke_manager",
]
