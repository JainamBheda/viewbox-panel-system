from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.survey import Survey, SurveyApplication, SurveyCompletion, SurveyRule
from app.services.eligibility_service import evaluate, recalculate_for_survey
from app.services.payout_service import ensure_survey_payout
from app.services import questionnaire_service


def list_surveys(db: Session, *, live_only: bool = False) -> list[Survey]:
    query = select(Survey)
    if live_only:
        query = query.where(Survey.status == "LIVE")
    return list(db.execute(query.order_by(Survey.deadline, Survey.id)).scalars().all())


def get_survey(db: Session, survey_id: int) -> Survey:
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


def create_survey(db: Session, data: dict, rules: list[dict]) -> Survey:
    survey = Survey(**data)
    db.add(survey)
    db.flush()
    _sync_rules(db, survey, rules)
    db.commit()
    db.refresh(survey)
    return survey


def update_survey(db: Session, survey_id: int, data: dict, rules: list[dict] | None) -> Survey:
    survey = get_survey(db, survey_id)
    for key, value in data.items():
        if value is not None:
            setattr(survey, key, value)
    if rules is not None:
        _sync_rules(db, survey, rules)
    db.commit()
    if rules is not None or any(key in data for key in ("deadline", "quota", "status")):
        recalculate_for_survey(db, survey.id)
    db.refresh(survey)
    return survey


def _sync_rules(db: Session, survey: Survey, rules: list[dict]) -> None:
    for rule in survey.rules:
        db.delete(rule)
    db.flush()
    for rule in rules:
        if rule.get("field_name") not in {"age", "city", "gender", "income_range", "interests"}:
            raise HTTPException(status_code=422, detail=f"Unsupported rule field: {rule.get('field_name')}")
        if rule.get("rule_type") not in {"STRICT", "FLEXIBLE"}:
            raise HTTPException(status_code=422, detail="rule_type must be STRICT or FLEXIBLE")
        db.add(SurveyRule(survey_id=survey.id, **rule))


def survey_for_member(db: Session, survey_id: int, member_id: int) -> dict:
    survey = get_survey(db, survey_id)
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    result = evaluate(db, survey, member)
    application = db.execute(
        select(SurveyApplication).where(
            SurveyApplication.survey_id == survey_id, SurveyApplication.member_id == member_id
        )
    ).scalars().first()
    return {
        "survey": survey,
        "eligibility": {"status": result.status, "reason": result.reason, "rule_results": result.rule_results},
        "application_status": application.eligibility_status if application else None,
        "has_questionnaire": questionnaire_service.has_active(db, survey.id),
    }


def record_completion(db: Session, survey_id: int, member_id: int, quality_status: str) -> SurveyCompletion:
    if quality_status not in {"PENDING", "PASSED", "FAILED"}:
        raise HTTPException(status_code=422, detail="Invalid quality status")
    survey = get_survey(db, survey_id)
    completion = db.execute(
        select(SurveyCompletion).where(
            SurveyCompletion.survey_id == survey_id, SurveyCompletion.member_id == member_id
        )
    ).scalars().first()
    if not completion:
        completion = SurveyCompletion(
            survey_id=survey_id, member_id=member_id, reward_amount=survey.reward_amount
        )
        db.add(completion)
    completion.quality_status = quality_status
    completion.completed_at = datetime.now(timezone.utc)
    member = db.get(Member, member_id)
    if quality_status == "PASSED":
        member.last_survey_completed_at = completion.completed_at
        ensure_survey_payout(db, member_id, completion)
    db.commit()

    from app.services.eligibility_service import recalculate_for_member

    recalculate_for_member(db, member_id)
    db.refresh(completion)
    return completion
