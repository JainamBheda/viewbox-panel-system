from tests.conftest import make_member, member_headers, referral_token, source_link

BASE_REGISTER = {
    "name": "New Person",
    "phone": "9812345678",
    "date_of_birth": "15/03/1995",
    "gender": "female",
    "city": "navi mumbai",
    "income_range": "6L-10L",
    "interests": "Tech;Travel",
}


def test_register_with_source_link(client, db, sources):
    link = source_link(db, sources["Instagram"], token="SRC-TEST01")
    response = client.post("/api/v1/public/register", json={**BASE_REGISTER, "source_token": link.token})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_id"] == sources["Instagram"].id
    assert body["gender"] == "FEMALE"
    assert body["city"] == "Navi Mumbai"


def test_register_with_referral_link(client, db, sources):
    referrer = make_member(db, phone="9011111111", code="VBREF01")
    response = client.post("/api/v1/public/register", json={**BASE_REGISTER, "referral_token": referral_token(db, referrer)})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["referred_by_member_id"] == referrer.id
    assert body["source_id"] == sources["Referral"].id


def test_source_and_referral_conflict_credits_both(client, db, sources):
    referrer = make_member(db, phone="9011111111", code="VBREF01")
    link = source_link(db, sources["Instagram"], token="SRC-TEST01")
    response = client.post("/api/v1/public/register", json={
        **BASE_REGISTER,
        "source_token": link.token,
        "referral_token": referral_token(db, referrer),
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_id"] == sources["Instagram"].id
    assert body["referred_by_member_id"] == referrer.id


def test_duplicate_phone_rejected_and_flagged(client, db):
    make_member(db, phone="9812345678", code="VBOLD001")
    response = client.post("/api/v1/public/register", json=BASE_REGISTER)
    assert response.status_code == 409
    from sqlalchemy import select
    from app.models.member import FraudFlag

    assert db.execute(select(FraudFlag).where(FraudFlag.flag_type == "DUPLICATE_PHONE")).first() is not None


def test_referrer_dashboard_masks_phone(client, db):
    referrer = make_member(db, phone="9011111111", code="VBREF01")
    response = client.post("/api/v1/public/register", json={**BASE_REGISTER, "referral_token": referral_token(db, referrer)})
    assert response.status_code == 200
    dashboard = client.get("/api/v1/members/me/referrals", headers=member_headers(referrer))
    assert dashboard.status_code == 200
    item = dashboard.json()[0]
    assert item["status"] == "LEAD"
    assert item["masked_phone"] == "+91 9•••• ••678"
    assert "9812345678" not in str(dashboard.json())
