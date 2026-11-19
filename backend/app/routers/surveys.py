from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.schemas.survey import ApplicationOut, CompletionIn, SurveyIn, SurveyOut, SurveyUpdate
from app.services import survey_service

router = APIRouter(tags=["surveys"])


@router.get("/surveys", response_model=list[SurveyOut])
def live_surveys(db: Session = Depends(get_db)):
    return survey_service.list_surveys(db, live_only=True)


admin_router = APIRouter(prefix="/admin/surveys", tags=["admin surveys"])


@admin_router.get("", response_model=list[SurveyOut])
def all_surveys(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return survey_service.list_surveys(db)


@admin_router.post("", response_model=SurveyOut, status_code=status.HTTP_201_CREATED)
def create_survey(payload: SurveyIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    data = payload.model_dump()
    return survey_service.create_survey(db, {key: value for key, value in data.items() if key != "rules"}, data["rules"])


@admin_router.patch("/{survey_id}", response_model=SurveyOut)
def update_survey(survey_id: int, payload: SurveyUpdate, db: Session = Depends(get_db),
                  admin: User = Depends(require_admin)):
    data = payload.model_dump(exclude_unset=True)
    return survey_service.update_survey(db, survey_id, data, data.pop("rules", None))


@admin_router.get("/{survey_id}/applications", response_model=list[ApplicationOut])
def applications(survey_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    from sqlalchemy import select
    from app.models.survey import SurveyApplication

    survey_service.get_survey(db, survey_id)
    return list(db.execute(
        select(SurveyApplication).where(SurveyApplication.survey_id == survey_id).order_by(SurveyApplication.id.desc())
    ).scalars().all())


@admin_router.post("/{survey_id}/completions/{member_id}")
def complete(survey_id: int, member_id: int, payload: CompletionIn, db: Session = Depends(get_db),
             admin: User = Depends(require_admin)):
    completion = survey_service.record_completion(db, survey_id, member_id, payload.quality_status)
    return {"id": completion.id, "quality_status": completion.quality_status, "member_id": member_id}
