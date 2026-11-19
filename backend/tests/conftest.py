import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.models.member import Member  # noqa: E402
from app.models.source import ReferralLink, Source, SourceLink  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.utils.tokens import unique_member_code, unique_referral_token, unique_source_token  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sources(db):
    result = {}
    for name, source_type in [("Instagram", "INSTAGRAM"), ("Facebook", "FACEBOOK"),
                              ("Referral", "REFERRAL"), ("Website", "WEBSITE")]:
        source = Source(name=name, source_type=source_type)
        db.add(source)
        db.flush()
        result[name] = source
    db.commit()
    return result


@pytest.fixture()
def admin(db):
    user = User(phone="9000000001", role="ADMIN")
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def admin_headers(admin):
    return {"Authorization": f"Bearer {create_access_token(str(admin.id), 'ADMIN')}"}


def make_member(db, *, phone="9012345678", code="VB10001", name="Test Member", source=None, referred_by=None,
                gender="MALE", city="Mumbai", income="6L-10L", interests=None, dob=None):
    from datetime import date

    user = User(phone=phone, role="MEMBER")
    db.add(user)
    db.flush()
    member = Member(
        member_code=code,
        user_id=user.id,
        name=name,
        date_of_birth=dob or date(1990, 1, 1),
        gender=gender,
        city=city,
        income_range=income,
        interests=interests or ["Tech", "Travel"],
        source_id=source.id if source else None,
        referred_by_member_id=referred_by.id if referred_by else None,
    )
    db.add(member)
    db.flush()
    db.add(ReferralLink(token=unique_referral_token(db), member_id=member.id))
    db.commit()
    return member


def member_headers(member):
    return {"Authorization": f"Bearer {create_access_token(str(member.user_id), 'MEMBER')}"}


def referral_token(db, member):
    from sqlalchemy import select
    return db.execute(select(ReferralLink).where(ReferralLink.member_id == member.id)).scalars().first().token


def source_link(db, source, token=None):
    link = SourceLink(token=token or unique_source_token(db), source_id=source.id, campaign_name="Test")
    db.add(link)
    db.commit()
    return link
