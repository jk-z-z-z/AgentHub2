from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.skill import SkillCreateRequest, SkillOut
from app.services.skill_service import create_skill, delete_skill, get_skill, list_skills, update_skill


router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=ApiResponse[list[SkillOut]])
def list_skills_api(db: Session = Depends(get_db)):
    rows = list_skills(db)
    return ApiResponse(data=[SkillOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[SkillOut])
def create_skill_api(payload: SkillCreateRequest, db: Session = Depends(get_db)):
    row = create_skill(db, payload.model_dump())
    return ApiResponse(data=SkillOut.model_validate(row))


@router.get("/{skill_id}", response_model=ApiResponse[SkillOut])
def get_skill_api(skill_id: int, db: Session = Depends(get_db)):
    row = get_skill(db, int(skill_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return ApiResponse(data=SkillOut.model_validate(row))


@router.put("/{skill_id}", response_model=ApiResponse[SkillOut])
def update_skill_api(skill_id: int, payload: SkillCreateRequest, db: Session = Depends(get_db)):
    try:
        row = update_skill(db, int(skill_id), payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return ApiResponse(data=SkillOut.model_validate(row))


@router.delete("/{skill_id}", response_model=ApiResponse[bool])
def delete_skill_api(skill_id: int, db: Session = Depends(get_db)):
    delete_skill(db, int(skill_id))
    return ApiResponse(data=True)
