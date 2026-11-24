"""v2 questionnaire authoring, runtime and analytics endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin, require_member
from app.models.member import Member
from app.models.questionnaire import QuestionnaireVersion
from app.models.user import User
from app.schemas.survey import AnswerIn, QuestionnaireTextIn, QuestionnaireVersionOut, RuntimeStepOut
from app.services import member_service, questionnaire_service, response_service, survey_service

router = APIRouter(prefix="/members/me/surveys/{survey_id}", tags=["member questionnaire"])
admin_router = APIRouter(prefix="/admin/surveys/{survey_id}", tags=["admin questionnaire"])


def _version_out(version) -> dict:
    return {
        "id": version.id,
        "survey_id": version.survey_id,
        "version": version.version,
        "status": version.status,
        "question_count": len(version.ast.get("questions", [])),
        "created_at": version.created_at,
    }


def _member_for(user: User, db: Session) -> Member:
    member = member_service.get_member_for_user(db, user.id)
    if not member:
        raise HTTPException(status_code=404, detail="Member profile not found")
    return member


@admin_router.post("/questionnaire/validate")
def validate_questionnaire(survey_id: int, payload: QuestionnaireTextIn, db: Session = Depends(get_db),
                           admin: User = Depends(require_admin)):
    survey_service.get_survey(db, survey_id)
    return questionnaire_service.parse_questionnaire(payload.text)


@admin_router.post("/questionnaire", response_model=QuestionnaireVersionOut)
def publish_questionnaire(survey_id: int, payload: QuestionnaireTextIn, db: Session = Depends(get_db),
                          admin: User = Depends(require_admin)):
    survey_service.get_survey(db, survey_id)
    return _version_out(questionnaire_service.publish(db, survey_id, payload.text))


@admin_router.get("/questionnaire/versions", response_model=list[QuestionnaireVersionOut])
def questionnaire_versions(survey_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    survey_service.get_survey(db, survey_id)
    versions = db.execute(
        select(QuestionnaireVersion)
        .where(QuestionnaireVersion.survey_id == survey_id)
        .order_by(QuestionnaireVersion.version.desc())
    ).scalars().all()
    return [_version_out(version) for version in versions]


@admin_router.get("/analytics")
def survey_analytics(survey_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return response_service.analytics(db, survey_id)


@router.post("/response/start", response_model=RuntimeStepOut)
def start_response(survey_id: int, user: User = Depends(require_member), db: Session = Depends(get_db)):
    return response_service.start_or_resume(db, survey_id, _member_for(user, db).id)


@router.get("/response", response_model=RuntimeStepOut)
def get_response(survey_id: int, user: User = Depends(require_member), db: Session = Depends(get_db)):
    return response_service.current(db, survey_id, _member_for(user, db).id)


@router.post("/response/answer", response_model=RuntimeStepOut)
def answer_response(survey_id: int, payload: AnswerIn, user: User = Depends(require_member),
                    db: Session = Depends(get_db)):
    return response_service.submit_answer(db, survey_id, _member_for(user, db).id,
                                          payload.question_id, payload.value)


@router.post("/response/back", response_model=RuntimeStepOut)
def back_response(survey_id: int, user: User = Depends(require_member), db: Session = Depends(get_db)):
    return response_service.go_back(db, survey_id, _member_for(user, db).id)
