from __future__ import annotations

from app.bootstrap_runtime.tool.builtins.file_delete import FileDeleteTool
from app.bootstrap_runtime.tool.builtins.file_list import FileListTool
from app.bootstrap_runtime.tool.builtins.file_read import FileReadTool
from app.bootstrap_runtime.tool.builtins.file_write import FileWriteTool


def get_bootstrap_tools() -> list[object]:
    return [FileListTool(), FileReadTool(), FileWriteTool(), FileDeleteTool()]
