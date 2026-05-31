from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.tool import ToolOut
from app.services.tool_service import list_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ApiResponse[list[ToolOut]])
def list_tools_api(db: Session = Depends(get_db)):
    rows = list_tools(db)
    return ApiResponse(data=[ToolOut.model_validate(row) for row in rows])
