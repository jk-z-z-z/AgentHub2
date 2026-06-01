from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCallResult:
    ok: bool
    result: dict
    error: str | None = None


class ManagerTool:
    code: str

    async def __call__(self, **kwargs) -> ToolCallResult:  # pragma: no cover
        raise NotImplementedError

