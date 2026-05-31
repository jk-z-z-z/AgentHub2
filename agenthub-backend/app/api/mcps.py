from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.mcp import MCPCreateRequest, MCPOut
from app.services.mcp_service import create_mcp, delete_mcp, list_mcps, update_mcp


router = APIRouter(prefix="/mcps", tags=["mcps"])


@router.get("", response_model=ApiResponse[list[MCPOut]])
def list_mcps_api(db: Session = Depends(get_db)):
    rows = list_mcps(db)
    return ApiResponse(data=[MCPOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[MCPOut])
def create_mcp_api(payload: MCPCreateRequest, db: Session = Depends(get_db)):
    row = create_mcp(db, payload.model_dump())
    return ApiResponse(data=MCPOut.model_validate(row))


@router.put("/{mcp_id}", response_model=ApiResponse[MCPOut])
def update_mcp_api(mcp_id: int, payload: MCPCreateRequest, db: Session = Depends(get_db)):
    try:
        row = update_mcp(db, mcp_id, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return ApiResponse(data=MCPOut.model_validate(row))


@router.delete("/{mcp_id}", response_model=ApiResponse[bool])
def delete_mcp_api(mcp_id: int, db: Session = Depends(get_db)):
    delete_mcp(db, mcp_id)
    return ApiResponse(data=True)
