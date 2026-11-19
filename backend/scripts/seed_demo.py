"""Idempotent demo data loader. Run: python -m scripts.seed_demo [--with-csv]"""

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.core.database import Base
from app.models import *  # noqa: F403 — register models
from app.models.member import Member
from app.models.survey import Survey
from app.models.user import User
from app.services import import_service
from app.services.auth_service import ensure_source
from app.services.source_service import ensure_referral_link
from app.utils.tokens import unique_referral_token, unique_source_token

DEMO_USERS = [
    ("9000000001", "ADMIN", "Concave Admin"),
    ("9000000002", "OPERATIONS", "Concave Operations"),
    ("9000000003", "MEMBER", "Aarav Demo"),
]

SOURCES = [
    ("Instagram", "INSTAGRAM"),
    ("Facebook", "FACEBOOK"),
    ("Website", "WEBSITE"),
    ("Referral", "REFERRAL"),
    ("WhatsApp Group - Mumbai", "WHATSAPP_GROUP"),
    ("WhatsApp Group - Pune", "WHATSAPP_GROUP"),
    ("Staff DM - Agent 01", "STAFF_DM"),
    ("Staff DM - Agent 02", "STAFF_DM"),
    ("Meta Ads", "META_ADS"),
]


def seed(csv_path: Path | None = None) -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for name, source_type in SOURCES:
            source = ensure_source(db, name, source_type)
            if not db.execute(select(SourceLink).where(SourceLink.source_id == source.id)).first():
                db.add(SourceLink(token=unique_source_token(db), source_id=source.id, campaign_name="Demo campaign"))

        for phone, role, name in DEMO_USERS:
            user = db.execute(select(User).where(User.phone == phone)).scalars().first()
            if not user:
                user = User(phone=phone, role=role)
                db.add(user)
                db.flush()
            member = db.execute(select(Member).where(Member.user_id == user.id)).scalars().first()
            if not member:
                member = Member(
                    member_code=f"VB{phone[-5:]}",
                    user_id=user.id,
                    name=name,
                    date_of_birth=date(1995, 6, 15),
                    gender="MALE",
                    city="Mumbai",
                    income_range="6L-10L",
                    interests=["Tech", "Travel", "Food"],
                    source_id=None,
                    joined_at=datetime.now(timezone.utc),
                )
                db.add(member)
                db.flush()
            ensure_referral_link(db, member.id)
            if role == "MEMBER":
                instagram = db.execute(select(Source).where(Source.name == "Instagram")).scalars().first()
                member.source_id = instagram.id
                member.first_touch_source_id = instagram.id
        db.flush()

        if not db.execute(select(Survey.id).where(Survey.title == "Urban Mobility Survey 2026")).first():
            db.add(Survey(
                title="Urban Mobility Survey 2026",
                description="20-minute survey about city commuting habits.",
                start_date=date.today(),
                deadline=date.today() + timedelta(days=30),
                quota=500,
                reward_amount=150,
                status="LIVE",
                rules=[
                    SurveyRule(field_name="age", operator="GTE", expected_value="18", rule_type="STRICT"),
                    SurveyRule(field_name="age", operator="LTE", expected_value="60", rule_type="STRICT"),
                    SurveyRule(field_name="city", operator="IN", expected_value="Mumbai,Navi Mumbai,Pune", rule_type="FLEXIBLE"),
                    SurveyRule(field_name="interests", operator="CONTAINS", expected_value="Travel", rule_type="FLEXIBLE"),
                ],
            ))
        if not db.execute(select(Survey.id).where(Survey.title == "Food Delivery Habits")).first():
            db.add(Survey(
                title="Food Delivery Habits",
                description="Closed survey used to demonstrate cool-off and history.",
                start_date=date.today() - timedelta(days=60),
                deadline=date.today() - timedelta(days=10),
                quota=200,
                reward_amount=100,
                status="CLOSED",
                rules=[SurveyRule(field_name="age", operator="GTE", expected_value="18", rule_type="STRICT")],
            ))
        db.commit()

        if csv_path and csv_path.exists():
            job = import_service.analyse(db, csv_path.name, csv_path.read_bytes())
            import_service.confirm(db, job.id, None)
        return {"status": "ok", "demo_users": len(DEMO_USERS), "sources": len(SOURCES)}
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-csv", action="store_true", help="Also import the provided sample CSV")
    args = parser.parse_args()
    csv_file = Path(__file__).resolve().parents[2] / "viewbox_respondents_sample.csv" if args.with_csv else None
    print(seed(csv_file))
