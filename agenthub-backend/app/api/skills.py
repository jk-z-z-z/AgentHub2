from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.skill import SkillCreateRequest, SkillOut
from app.services.skill_service import create_skill, list_skills


router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=ApiResponse[list[SkillOut]])
def list_skills_api(db: Session = Depends(get_db)):
    rows = list_skills(db)
    return ApiResponse(data=[SkillOut.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse[SkillOut])
def create_skill_api(payload: SkillCreateRequest, db: Session = Depends(get_db)):
    row = create_skill(db, payload.model_dump())
    return ApiResponse(data=SkillOut.model_validate(row))
