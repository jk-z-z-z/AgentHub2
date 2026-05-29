from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.mcp import MCPCreateRequest, MCPOut
from app.services.mcp_service import create_mcp, list_mcps


router = APIRouter(prefix="/mcps", tags=["mcps"])


@router.get("", response_model=ApiResponse[list[MCPOut]])
def list_mcps_api(db: Session = Depends(get_db)):
    rows = list_mcps(db)
    return ApiResponse(data=[MCPOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[MCPOut])
def create_mcp_api(payload: MCPCreateRequest, db: Session = Depends(get_db)):
    row = create_mcp(db, payload.model_dump())
    return ApiResponse(data=MCPOut.model_validate(row))
