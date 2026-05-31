from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.tool import ToolOut
from app.services.tool_service import get_tool, list_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ApiResponse[list[ToolOut]])
def list_tools_api(db: Session = Depends(get_db)):
    rows = list_tools(db)
    return ApiResponse(data=[ToolOut.model_validate(row) for row in rows])


@router.get("/{tool_id}", response_model=ApiResponse[ToolOut])
def get_tool_api(tool_id: int, db: Session = Depends(get_db)):
    row = get_tool(db, int(tool_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return ApiResponse(data=ToolOut.model_validate(row))
