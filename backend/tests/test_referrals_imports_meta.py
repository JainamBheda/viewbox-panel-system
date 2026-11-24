import csv
import io
from datetime import date, timedelta

from app.core.security import create_access_token
from app.models.member import Member
from app.models.survey import Survey, SurveyCompletion, SurveyRule
from app.models.user import User
from tests.conftest import make_member, member_headers

CSV_HEADER = ["member_id", "name", "phone", "email", "gender", "date_of_birth", "city",
              "income_range", "interests", "source", "referred_by", "joined_on", "last_survey_completed_on"]


def csv_bytes(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def test_referral_stages_and_quality_gate(client, db, admin_headers):
    referrer = make_member(db, phone="9011111111", code="VBREF01")
    invited = make_member(db, phone="9022222222", code="VBREF02")
    from app.models.member import Referral
    referral = Referral(referrer_member_id=referrer.id, referred_member_id=invited.id, status="LEAD")
    db.add(referral)
    db.commit()

    assert client.patch(f"/api/v1/admin/referrals/{referral.id}/stage",
                        json={"status": "FIT"}, headers=admin_headers).status_code == 200
    blocked = client.patch(f"/api/v1/admin/referrals/{referral.id}/stage",
                           json={"status": "COMPLETED"}, headers=admin_headers)
    assert blocked.status_code == 409

    survey = Survey(title="S", deadline=date.today() + timedelta(days=5), quota=10, reward_amount=50)
    db.add(survey)
    db.flush()
    db.add(SurveyCompletion(survey_id=survey.id, member_id=invited.id, quality_status="PASSED"))
    db.commit()
    done = client.patch(f"/api/v1/admin/referrals/{referral.id}/stage",
                        json={"status": "COMPLETED"}, headers=admin_headers)
    assert done.status_code == 200
    assert done.json()["status"] == "COMPLETED"

    failed = client.patch(f"/api/v1/admin/referrals/{referral.id}/stage",
                          json={"status": "FAILED", "failure_reason": "Quality review failed"}, headers=admin_headers)
    assert failed.status_code == 200
    dashboard = client.get("/api/v1/members/me/referrals", headers=member_headers(referrer)).json()
    assert dashboard[0]["failure_reason"] == "Quality review failed"


def test_csv_malformed_rows_and_preview(client, db, admin_headers):
    content = csv_bytes([
        ["VB20001", "Good Person", "9988776655", "good@example.com", "F", "1995-05-05", "mumbai", "3L-6L",
         "Tech", "insta", "", "2026-01-01", ""],
        ["VB20002", "Bad Phone", "123", "bad@example.com", "M", "1995-05-05", "Pune", "3L-6L",
         "Tech", "FB", "", "2026-01-01", ""],
        ["VB20003", "Bad Date", "9988776654", "", "F", "31/02/1995", "Pune", "3L-6L",
         "Tech", "FB", "", "2026-01-01", ""],
        ["", "", "", "", "", "", "", "", "", "", "", "", ""],
    ])
    response = client.post("/api/v1/admin/imports/upload", files={"file": ("messy.csv", content, "text/csv")},
                           headers=admin_headers)
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]
    preview = client.get(f"/api/v1/admin/imports/{job_id}/preview", headers=admin_headers).json()
    assert preview["summary"]["total_rows"] == 4
    assert preview["summary"]["valid_rows"] == 1
    assert preview["summary"]["skipped_rows"] == 3

    confirmed = client.post(f"/api/v1/admin/imports/{job_id}/confirm", headers=admin_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["imported_rows"] == 1
    members = db.query(Member).all()
    assert len(members) == 1
    assert members[0].city == "Mumbai"
    report = client.get(f"/api/v1/admin/imports/{job_id}/errors.csv", headers=admin_headers)
    assert report.status_code == 200
    assert "INVALID_PHONE" in report.text and "INVALID_DOB" in report.text and "BLANK_ROW" in report.text


def test_csv_duplicate_import_idempotent(client, db, admin_headers):
    content = csv_bytes([
        ["VB30001", "One Person", "9988776655", "one@example.com", "M", "1990-01-01", "Pune", "3L-6L",
         "Tech", "insta", "", "2026-01-01", ""],
    ])
    first = client.post("/api/v1/admin/imports/upload", files={"file": ("same.csv", content, "text/csv")},
                        headers=admin_headers).json()
    second = client.post("/api/v1/admin/imports/upload", files={"file": ("same.csv", content, "text/csv")},
                         headers=admin_headers).json()
    assert first["id"] == second["id"]
    client.post(f"/api/v1/admin/imports/{first['id']}/confirm", headers=admin_headers)
    third = client.post("/api/v1/admin/imports/upload", files={"file": ("same.csv", content, "text/csv")},
                        headers=admin_headers).json()
    assert third["id"] == first["id"]
    assert db.query(Member).count() == 1


def test_meta_lead_idempotency(client, db):
    payload = {
        "meta_lead_id": "123123123123", "form_id": "999", "campaign_id": "888", "ad_id": "777",
        "created_time": 1440120384,
        "field_data": [
            {"name": "full_name", "values": ["Joe Example"]},
            {"name": "phone", "values": ["+91 99887 76655"]},
            {"name": "city", "values": ["Mumbai"]},
        ],
    }
    first = client.post("/api/v1/webhooks/meta/leads", json=payload)
    assert first.status_code == 200
    assert first.json()["result"] == "created"
    second = client.post("/api/v1/webhooks/meta/leads", json=payload)
    assert second.json()["result"] == "already_processed"
    assert db.query(Member).count() == 1


def test_meta_lead_missing_phone_flagged(client, db):
    payload = {"meta_lead_id": "444", "field_data": [{"name": "full_name", "values": ["No Phone"]}]}
    response = client.post("/api/v1/webhooks/meta/leads", json=payload)
    assert response.json()["result"] == "flagged"
    assert db.query(Member).count() == 0


def test_admin_export_respects_filters(client, db, admin_headers, sources):
    make_member(db, phone="9011111111", code="VB80001", city="Mumbai", source=sources["Instagram"])
    make_member(db, phone="9022222222", code="VB80002", city="Pune", source=sources["Facebook"])
    response = client.get("/api/v1/admin/members/export?format=csv&city=Mumbai", headers=admin_headers)
    assert response.status_code == 200
    assert "VB80001" in response.text
    assert "VB80002" not in response.text
    xlsx = client.get("/api/v1/admin/members/export?format=xlsx", headers=admin_headers)
    assert xlsx.status_code == 200
    assert xlsx.content[:2] == b"PK"


def test_export_escapes_spreadsheet_formulas(client, db, admin_headers):
    make_member(db, phone="9033333333", code="VB80003", city="Mumbai", name="=HYPERLINK(\"http://evil\",\"click\")")
    response = client.get("/api/v1/admin/members/export?format=csv&city=Mumbai", headers=admin_headers)
    assert response.status_code == 200
    assert "'=HYPERLINK" in response.text
    rows = list(csv.reader(io.StringIO(response.text.lstrip("\ufeff"))))
    assert rows[1][1] == "'=HYPERLINK(\"http://evil\",\"click\")"
