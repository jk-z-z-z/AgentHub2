from pydantic import Field

from app.schemas.common import ORMBaseModel


class TextFileOut(ORMBaseModel):
    path: str
    content: str


class TextFileWriteRequest(ORMBaseModel):
    content: str = Field(default="", max_length=2000000)


class FsEntryOut(ORMBaseModel):
    path: str
    is_dir: bool
    size: int = 0

