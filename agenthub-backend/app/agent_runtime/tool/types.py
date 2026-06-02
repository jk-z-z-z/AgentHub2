from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


ToolHandler = Callable[[int, dict, dict | None, dict], dict]


@dataclass(frozen=True)
class BuiltinToolDef:
    spec: dict
    handler: ToolHandler

