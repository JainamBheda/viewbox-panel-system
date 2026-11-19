from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.member import Member
from app.models.source import AttributionHistory, ReferralLink, Source, SourceLink
from app.models.user import OtpChallenge, User
from app.utils.phones import normalize_phone
from app.utils.tokens import unique_member_code, unique_referral_token


def request_otp(db: Session, phone: str) -> dict:
    normalized, valid = normalize_phone(phone)
    if not valid:
        raise HTTPException(status_code=422, detail="Enter a valid 10-digit Indian mobile number")
    challenge = OtpChallenge(
        phone=normalized,
        otp=settings.MOCK_OTP,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
    )
    db.add(challenge)
    db.commit()
    return {
        "message": "OTP created",
        "phone": normalized,
        "dev_otp": settings.MOCK_OTP if settings.ENVIRONMENT != "production" else None,
        "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
    }


def verify_otp(db: Session, phone: str, otp: str) -> dict:
    normalized, valid = normalize_phone(phone)
    if not valid:
        raise HTTPException(status_code=422, detail="Enter a valid 10-digit Indian mobile number")

    challenge = db.execute(
        select(OtpChallenge)
        .where(
            OtpChallenge.phone == normalized,
            OtpChallenge.otp == otp,
            OtpChallenge.verified_at.is_(None),
            OtpChallenge.expires_at > datetime.now(timezone.utc),
        )
        .order_by(OtpChallenge.id.desc())
    ).scalars().first()
    if not challenge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid, used or expired OTP")

    challenge.verified_at = datetime.now(timezone.utc)
    user = db.execute(select(User).where(User.phone == normalized)).scalars().first()
    if not user:
        user = User(phone=normalized, role="MEMBER", is_active=True)
        db.add(user)
        db.flush()

    member = db.execute(select(Member).where(Member.user_id == user.id)).scalars().first()
    if not member:
        member = Member(
            member_code=unique_member_code(db),
            user_id=user.id,
            name="(profile incomplete)",
            joined_at=datetime.now(timezone.utc),
        )
        db.add(member)
        db.flush()
        link = ReferralLink(token=unique_referral_token(db), member_id=member.id)
        db.add(link)
        db.add(
            AttributionHistory(
                member_id=member.id,
                attribution_type="MANUAL",
                touch="FIRST",
                raw_value={"channel": "OTP login"},
            )
        )

    db.commit()
    return {
        "access_token": create_access_token(str(user.id), user.role),
        "token_type": "bearer",
        "role": user.role,
        "member_id": member.id if member else None,
        "profile_complete": bool(member and member.name != "(profile incomplete)"),
    }


def ensure_source(db: Session, name: str, source_type: str = "OTHER") -> Source:
    source = db.execute(select(Source).where(Source.name == name)).scalars().first()
    if not source:
        source = Source(name=name, source_type=source_type, is_active=True)
        db.add(source)
        db.flush()
    return source


def resolve_attribution(db: Session, token: str | None, how_heard: str | None,
                        referral_token: str | None = None) -> dict:
    """Resolve source links and referral links. Both can coexist (source conflict rule)."""
    result = {"source_id": None, "source_name": None, "referrer_member_id": None, "referral_token": None, "errors": []}
    unknown: list[str] = []
    for candidate in (token, referral_token):
        if not candidate:
            continue
        source_link = db.execute(
            select(SourceLink).where(SourceLink.token == candidate, SourceLink.is_active.is_(True))
        ).scalars().first()
        if source_link:
            result["source_id"] = source_link.source_id
            result["source_name"] = source_link.source.name if source_link.source else None
            continue
        referral_link = db.execute(
            select(ReferralLink).where(ReferralLink.token == candidate, ReferralLink.is_active.is_(True))
        ).scalars().first()
        if referral_link:
            result["referrer_member_id"] = referral_link.member_id
            result["referral_token"] = candidate
        else:
            unknown.append(candidate)
    if unknown and result["source_id"] is None and result["referrer_member_id"] is None:
        result["errors"].append(f"Unknown or inactive attribution token '{unknown[0]}'")
    if how_heard and not result["source_id"]:
        source = db.execute(select(Source).where(Source.name.ilike(how_heard.strip()))).scalars().first()
        if source:
            result["source_id"] = source.id
            result["source_name"] = source.name
        else:
            result["errors"].append(f"Unknown source '{how_heard}'")
    return result
