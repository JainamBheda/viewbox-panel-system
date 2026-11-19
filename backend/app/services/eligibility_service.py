"""Deterministic eligibility engine: rules, deadline, calendar cool-off, quota."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.survey import Survey, SurveyApplication, SurveyCompletion, SurveyRule
from app.utils.dates import add_calendar_months, display_date


@dataclass
class EligibilityResult:
    status: str
    reason: str
    rule_results: list[dict]


COOL_OFF_MONTHS = 3


def _age_on(member: Member, today: date) -> int | None:
    if not member.date_of_birth:
        return None
    dob = member.date_of_birth
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _rule_passes(member: Member, rule: SurveyRule, today: date) -> bool:
    field = rule.field_name.lower()
    expected = str(rule.expected_value).strip()
    operator = rule.operator.upper()
    if field == "age":
        actual = _age_on(member, today)
        if actual is None:
            return False
        targets = [int(item) for item in expected.replace(" ", "").split(",") if item.lstrip("-").isdigit()]
        if not targets:
            return False
        if operator == "GTE":
            return actual >= targets[0]
        if operator == "LTE":
            return actual <= targets[0]
        if operator == "EQ":
            return actual == targets[0]
        if operator == "IN":
            return actual in targets
        return False

    if field == "interests":
        actual_values = [str(item).lower() for item in (member.interests or [])]
        wanted = [item.strip().lower() for item in expected.replace(",", ";").split(";") if item.strip()]
        if operator == "CONTAINS":
            return any(item in actual_values for item in wanted)
        if operator == "ALL":
            return all(item in actual_values for item in wanted)
        return False

    actual = None
    if field == "city":
        actual = member.city
    elif field == "gender":
        actual = member.gender
    elif field == "income_range":
        actual = member.income_range
    if actual is None:
        return False
    actual_text = str(actual).strip().lower()
    options = [item.strip().lower() for item in expected.split(",")]
    if operator == "EQ":
        return actual_text == options[0]
    if operator == "IN":
        return actual_text in options
    if operator == "CONTAINS":
        return any(item in actual_text for item in options)
    return False


def evaluate(db: Session, survey: Survey, member: Member, *, lock_quota: bool = False) -> EligibilityResult:
    today = date.today()
    rule_results: list[dict] = []
    strict_failures: list[str] = []
    flexible_failures: list[str] = []
    for rule in survey.rules:
        passed = _rule_passes(member, rule, today)
        label = f"{rule.field_name} {rule.operator} {rule.expected_value}"
        rule_results.append({"rule_id": rule.id, "label": label, "rule_type": rule.rule_type, "passed": passed})
        if not passed:
            (strict_failures if rule.rule_type == "STRICT" else flexible_failures).append(label)

    if survey.deadline and survey.deadline < today:
        return EligibilityResult("REJECTED", f"Survey deadline passed on {display_date(survey.deadline)}.", rule_results)
    if strict_failures:
        return EligibilityResult(
            "REJECTED", "Strict criteria not met: " + "; ".join(strict_failures) + ".", rule_results
        )

    last_completion = db.execute(
        select(SurveyCompletion)
        .where(
            SurveyCompletion.member_id == member.id,
            SurveyCompletion.quality_status == "PASSED",
        )
        .order_by(SurveyCompletion.completed_at.desc())
    ).scalars().first()
    if last_completion:
        eligible_again = add_calendar_months(last_completion.completed_at.date(), COOL_OFF_MONTHS)
        if today < eligible_again:
            return EligibilityResult(
                "REJECTED",
                f"3-month cool-off active after your last completed survey. Eligible again on {display_date(eligible_again)}.",
                rule_results,
            )

    if lock_quota:
        db.execute(select(Survey.id).where(Survey.id == survey.id).with_for_update())
    approved = db.execute(
        select(func.count(SurveyApplication.id)).where(
            SurveyApplication.survey_id == survey.id,
            SurveyApplication.eligibility_status == "APPROVED",
        )
    ).scalar() or 0
    if approved >= survey.quota:
        return EligibilityResult("REJECTED", "Survey quota is full.", rule_results)

    if flexible_failures:
        return EligibilityResult("WAITLISTED", "You are waitlisted: " + "; ".join(flexible_failures) + ".", rule_results)
    return EligibilityResult("APPROVED", "You meet all criteria for this survey.", rule_results)


def _upsert_application(db: Session, survey_id: int, member_id: int, result: EligibilityResult) -> SurveyApplication:
    application = db.execute(
        select(SurveyApplication).where(
            SurveyApplication.survey_id == survey_id, SurveyApplication.member_id == member_id
        )
    ).scalars().first()
    if application:
        application.eligibility_status = result.status
        application.reason = result.reason
        application.rule_results = result.rule_results
        application.updated_at = datetime.now(timezone.utc)
    else:
        application = SurveyApplication(
            survey_id=survey_id,
            member_id=member_id,
            eligibility_status=result.status,
            reason=result.reason,
            rule_results=result.rule_results,
        )
        db.add(application)
    return application


def apply_to_survey(db: Session, survey: Survey, member: Member) -> SurveyApplication:
    result = evaluate(db, survey, member, lock_quota=True)
    application = _upsert_application(db, survey.id, member.id, result)
    db.commit()
    db.refresh(application)
    return application


def recalculate_for_member(db: Session, member_id: int) -> int:
    member = db.get(Member, member_id)
    if not member:
        return 0
    surveys = db.execute(select(Survey).where(Survey.status == "LIVE")).scalars().all()
    for survey in surveys:
        _upsert_application(db, survey.id, member.id, evaluate(db, survey, member))
    db.commit()
    return len(surveys)


def recalculate_for_survey(db: Session, survey_id: int) -> int:
    survey = db.get(Survey, survey_id)
    if not survey:
        return 0
    members = db.execute(
        select(Member).join(SurveyApplication, SurveyApplication.member_id == Member.id)
        .where(SurveyApplication.survey_id == survey_id)
    ).scalars().all()
    for member in members:
        _upsert_application(db, survey_id, member.id, evaluate(db, survey, member))
    db.commit()
    return len(members)
