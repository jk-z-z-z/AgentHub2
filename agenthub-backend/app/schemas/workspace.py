from pydantic import Field

from app.schemas.common import ORMBaseModel


class WorkspaceFileInfo(ORMBaseModel):
    name: str
    exists: bool
    size: int
    enabled: bool


class WorkspaceFileListOut(ORMBaseModel):
    files: list[WorkspaceFileInfo]


class WorkspaceFileContentOut(ORMBaseModel):
    name: str
    content: str


class WorkspaceFileWriteRequest(ORMBaseModel):
    content: str = Field(default="", max_length=500000)


class WorkspaceFileTogglesRequest(ORMBaseModel):
    toggles: dict[str, bool] = Field(default_factory=dict)


class WorkspaceFileTogglesOut(ORMBaseModel):
    enabled_files: dict[str, bool]

