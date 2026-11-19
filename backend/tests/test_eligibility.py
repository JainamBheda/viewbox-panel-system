from datetime import date, datetime, timedelta, timezone

from app.models.survey import Survey, SurveyApplication, SurveyCompletion, SurveyRule
from app.services.eligibility_service import evaluate
from tests.conftest import make_member, member_headers


def make_survey(db, **kwargs):
    survey = Survey(
        title=kwargs.pop("title", "Test Survey"),
        deadline=kwargs.pop("deadline", date.today() + timedelta(days=10)),
        quota=kwargs.pop("quota", 10),
        status=kwargs.pop("status", "LIVE"),
        reward_amount=kwargs.pop("reward_amount", 100),
    )
    db.add(survey)
    db.flush()
    for rule in kwargs.pop("rules", []):
        db.add(SurveyRule(survey_id=survey.id, **rule))
    db.commit()
    return survey


def test_strict_rule_failure(client, db):
    member = make_member(db)
    survey = make_survey(db, rules=[{"field_name": "city", "operator": "EQ", "expected_value": "Delhi", "rule_type": "STRICT"}])
    response = client.get("/api/v1/members/me/surveys", headers=member_headers(member))
    result = next(item for item in response.json() if item["survey"]["id"] == survey.id)["eligibility"]
    assert result["status"] == "REJECTED"
    assert "Strict criteria not met" in result["reason"]


def test_flexible_rule_failure_waits(client, db):
    member = make_member(db)
    survey = make_survey(db, rules=[
        {"field_name": "age", "operator": "GTE", "expected_value": "18", "rule_type": "STRICT"},
        {"field_name": "interests", "operator": "CONTAINS", "expected_value": "Finance", "rule_type": "FLEXIBLE"},
    ])
    result = evaluate(db, survey, member)
    assert result.status == "WAITLISTED"
    assert "waitlisted" in result.reason.lower()


def test_all_rules_pass_approved(db):
    member = make_member(db)
    survey = make_survey(db, rules=[
        {"field_name": "age", "operator": "GTE", "expected_value": "18", "rule_type": "STRICT"},
        {"field_name": "city", "operator": "EQ", "expected_value": "Mumbai", "rule_type": "STRICT"},
    ])
    result = evaluate(db, survey, member)
    assert result.status == "APPROVED"


def test_quota_reached(db):
    member = make_member(db)
    other = make_member(db, phone="9011111112", code="VB10002")
    survey = make_survey(db, quota=1)
    db.add(SurveyApplication(survey_id=survey.id, member_id=other.id, eligibility_status="APPROVED", reason="test"))
    db.commit()
    assert evaluate(db, survey, member).status == "REJECTED"
    assert "quota" in evaluate(db, survey, member).reason.lower()


def test_deadline_passed(db):
    member = make_member(db)
    survey = make_survey(db, deadline=date.today() - timedelta(days=1))
    result = evaluate(db, survey, member)
    assert result.status == "REJECTED"
    assert "deadline" in result.reason.lower()


def test_three_month_calendar_cool_off(db):
    member = make_member(db)
    survey = make_survey(db)
    last_completed = date.today().replace(day=1) - timedelta(days=1)  # previous month
    db.add(SurveyCompletion(
        survey_id=survey.id,
        member_id=member.id,
        completed_at=datetime(last_completed.year, last_completed.month, 15, tzinfo=timezone.utc),
        quality_status="PASSED",
    ))
    db.commit()
    result = evaluate(db, survey, member)
    assert result.status == "REJECTED"
    assert "Eligible again on " in result.reason

    from app.utils.dates import add_calendar_months, display_date

    expected = display_date(add_calendar_months(last_completed.replace(day=15), 3))
    assert expected in result.reason


def test_failed_completion_does_not_trigger_cool_off(db):
    member = make_member(db)
    survey = make_survey(db)
    db.add(SurveyCompletion(
        survey_id=survey.id, member_id=member.id,
        completed_at=datetime.now(timezone.utc), quality_status="FAILED",
    ))
    db.commit()
    assert evaluate(db, survey, member).status == "APPROVED"
