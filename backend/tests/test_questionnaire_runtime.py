from datetime import date, timedelta

from app.models.questionnaire import QuestionnaireVersion, SurveyResponse
from app.models.survey import Survey, SurveyApplication, SurveyCompletion
from app.services import questionnaire_service
from tests.conftest import make_member, member_headers

QUESTIONNAIRE = """Q1 | single | What is your primary commute mode? | Car | Bike
Q2 | multi | Which factors matter? | Price | Safety | Time
Q3 | rating | How satisfied are you? | 1-5
"""


def _approved_survey(db, *, title="Runtime survey", quota=10):
    member = make_member(db, phone="9099999901", code="VB99001")
    survey = Survey(
        title=title,
        description="Questionnaire runtime test",
        deadline=date.today() + timedelta(days=10),
        quota=quota,
        reward_amount=50,
        status="LIVE",
    )
    db.add(survey)
    db.flush()
    db.add(SurveyApplication(
        survey_id=survey.id,
        member_id=member.id,
        eligibility_status="APPROVED",
        reason="Approved for test",
        rule_results=[],
    ))
    db.commit()
    return survey, member


def test_validation_returns_line_numbered_errors(client, db, admin_headers):
    survey, _ = _approved_survey(db)
    response = client.post(
        f"/api/v1/admin/surveys/{survey.id}/questionnaire/validate",
        json={"text": "Q1 | single | Pick one\nBAD LINE\n"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert {error["code"] for error in body["errors"]} >= {"MISSING_OPTIONS", "UNKNOWN_DIRECTIVE"}
    assert any(error["line"] == 2 for error in body["errors"])


def test_publish_version_is_visible_to_member(client, db, admin_headers):
    survey, member = _approved_survey(db)
    response = client.post(
        f"/api/v1/admin/surveys/{survey.id}/questionnaire",
        json={"text": QUESTIONNAIRE},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 1
    assert response.json()["question_count"] == 3

    members_view = client.get("/api/v1/members/me/surveys", headers=member_headers(member))
    assert members_view.status_code == 200
    assert any(item["has_questionnaire"] for item in members_view.json())

    versions = db.query(QuestionnaireVersion).all()
    assert len(versions) == 1
    assert versions[0].ast["questions"][0]["id"] == "Q1"


def test_member_can_answer_questionnaire_to_completion(client, db, admin_headers):
    survey, member = _approved_survey(db)
    published = client.post(
        f"/api/v1/admin/surveys/{survey.id}/questionnaire",
        json={"text": QUESTIONNAIRE},
        headers=admin_headers,
    )
    assert published.status_code == 200

    headers = member_headers(member)
    start = client.post(f"/api/v1/members/me/surveys/{survey.id}/response/start", headers=headers)
    assert start.status_code == 200, start.text
    assert start.json()["question"]["id"] == "Q1"

    answer1 = client.post(
        f"/api/v1/members/me/surveys/{survey.id}/response/answer",
        json={"question_id": "Q1", "value": "Car"},
        headers=headers,
    )
    assert answer1.json()["question"]["id"] == "Q2"

    answer2 = client.post(
        f"/api/v1/members/me/surveys/{survey.id}/response/answer",
        json={"question_id": "Q2", "value": ["Price", "Safety"]},
        headers=headers,
    )
    assert answer2.json()["question"]["id"] == "Q3"

    answer3 = client.post(
        f"/api/v1/members/me/surveys/{survey.id}/response/answer",
        json={"question_id": "Q3", "value": 5},
        headers=headers,
    )
    assert answer3.json()["status"] == "COMPLETED", answer3.text
    assert answer3.json()["question"] is None

    response_row = db.query(SurveyResponse).one()
    assert response_row.status == "COMPLETED"
    assert response_row.answers == {"Q1": "Car", "Q2": ["Price", "Safety"], "Q3": 5}
    assert db.query(SurveyCompletion).filter_by(survey_id=survey.id, member_id=member.id).one()

    analytics = client.get(
        f"/api/v1/admin/surveys/{survey.id}/analytics",
        headers=admin_headers,
    )
    assert analytics.status_code == 200
    assert analytics.json()["completed"] == 1
    assert any(item["id"] == "Q1" and item["answered"] == 1 for item in analytics.json()["questions"])


def test_condition_engine_and_piping():
    ast = questionnaire_service.parse_questionnaire(
        "Q1 | single | Mode? | Car | Bike\nQ2 | text | Why did you choose {Q1}?\nSHOW | Q2 | IF | Q1 | EQ | Car\n"
    )
    assert ast["valid"], ast["errors"]
    assert ast["questions"][1]["text"] == "Why did you choose {Q1}?"
    question, reason = questionnaire_service.next_question(ast, {"Q1": "Car"})
    assert reason is None
    assert question["text"] == "Why did you choose Car?"
    hidden, reason = questionnaire_service.next_question(ast, {"Q1": "Bike"})
    assert hidden is None and reason is None


FULL_DSL = """Q1 | single | Mode? | Car | Bike | Walk
Q2 | multi | Factors? | Price | Safety
Q3 | rating | Satisfaction? | 1-5
SHOW | Q2 | IF | Q1 | EQ | Car
SKIP | Q3 | IF | Q1 | EQ | Bike
TERMINATE | IF | Q1 | EQ | Walk | Walkers are out of scope
QUOTA | Q1 | Car | 5
"""


def test_full_dsl_validates_and_versions_archive_previous(client, db, admin_headers):
    parsed = questionnaire_service.parse_questionnaire(FULL_DSL)
    assert parsed["valid"], parsed["errors"]
    assert parsed["quotas"][0]["quota_target"] == 5

    survey, _ = _approved_survey(db, title="Versioned survey")
    first = client.post(f"/api/v1/admin/surveys/{survey.id}/questionnaire",
                        json={"text": FULL_DSL}, headers=admin_headers)
    second = client.post(f"/api/v1/admin/surveys/{survey.id}/questionnaire",
                         json={"text": QUESTIONNAIRE}, headers=admin_headers)
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2, second.text

    versions = {row.version: row.status for row in db.query(QuestionnaireVersion).all()}
    assert versions == {1: "ARCHIVED", 2: "ACTIVE"}


def test_screener_termination_is_persisted(client, db, admin_headers):
    survey, member = _approved_survey(db, title="Screener survey")
    published = client.post(f"/api/v1/admin/surveys/{survey.id}/questionnaire",
                            json={"text": FULL_DSL}, headers=admin_headers)
    assert published.status_code == 200

    headers = member_headers(member)
    assert client.post(f"/api/v1/members/me/surveys/{survey.id}/response/start", headers=headers).status_code == 200
    result = client.post(
        f"/api/v1/members/me/surveys/{survey.id}/response/answer",
        json={"question_id": "Q1", "value": "Walk"},
        headers=headers,
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "TERMINATED"
    assert result.json()["termination_reason"] == "Walkers are out of scope"

    row = db.query(SurveyResponse).one()
    assert row.status == "TERMINATED"
    assert row.termination_reason == "Walkers are out of scope"
    assert db.query(SurveyCompletion).count() == 0

    again = client.post(
        f"/api/v1/members/me/surveys/{survey.id}/response/answer",
        json={"value": "Car"}, headers=headers,
    )
    assert again.status_code == 409
