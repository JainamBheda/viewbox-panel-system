from app.core.security import create_access_token
from app.models.user import User


def test_request_otp_returns_dev_code(client):
    response = client.post("/api/v1/auth/request-otp", json={"phone": "9876543210"})
    assert response.status_code == 200
    assert response.json()["dev_otp"] == "123456"


def test_verify_otp_creates_member_and_link(client):
    client.post("/api/v1/auth/request-otp", json={"phone": "9876543210"})
    response = client.post("/api/v1/auth/verify-otp", json={"phone": "9876543210", "otp": "123456"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "MEMBER"
    assert body["member_id"] is not None
    assert body["profile_complete"] is False

    link = client.get("/api/v1/members/me/referral-link", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert link.status_code == 200
    assert link.json()["token"].startswith("REF-")


def test_otp_cannot_be_reused(client):
    client.post("/api/v1/auth/request-otp", json={"phone": "9876543210"})
    payload = {"phone": "9876543210", "otp": "123456"}
    assert client.post("/api/v1/auth/verify-otp", json=payload).status_code == 200
    assert client.post("/api/v1/auth/verify-otp", json=payload).status_code == 400


def test_wrong_otp_rejected(client):
    client.post("/api/v1/auth/request-otp", json={"phone": "9876543210"})
    response = client.post("/api/v1/auth/verify-otp", json={"phone": "9876543210", "otp": "000000"})
    assert response.status_code == 400


def test_unauthorized_admin_operations(client, db):
    user = User(phone="9000000009", role="MEMBER")
    db.add(user)
    db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id), 'MEMBER')}"}
    assert client.get("/api/v1/admin/members", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/sources", headers=headers).status_code == 403
