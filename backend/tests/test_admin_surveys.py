from datetime import date, timedelta


def test_create_survey_with_explicit_status(client, admin_headers):
    payload = {
        "title": "Regression survey",
        "description": "Explicit status must not be passed twice to the model",
        "deadline": str(date.today() + timedelta(days=10)),
        "quota": 5,
        "reward_amount": 75,
        "status": "LIVE",
        "rules": [
            {
                "field_name": "age",
                "operator": "GTE",
                "expected_value": "18",
                "rule_type": "STRICT",
            }
        ],
    }

    response = client.post("/api/v1/admin/surveys", json=payload, headers=admin_headers)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["status"] == "LIVE"
    assert len(body["rules"]) == 1


def test_create_survey_defaults_to_draft(client, admin_headers):
    payload = {
        "title": "Default status survey",
        "deadline": str(date.today() + timedelta(days=10)),
    }

    response = client.post("/api/v1/admin/surveys", json=payload, headers=admin_headers)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "DRAFT"
