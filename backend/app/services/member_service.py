from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.member import FraudFlag, Member, Referral
from app.models.source import AttributionHistory, ReferralLink, Source
from app.models.survey import SurveyApplication
from app.models.user import User
from app.services.auth_service import ensure_source, resolve_attribution
from app.utils.dates import parse_date
from app.utils.normalization import normalize_city, normalize_gender, normalize_income, normalize_interests
from app.utils.phones import normalize_phone
from app.utils.tokens import unique_member_code, unique_referral_token


def flag(db: Session, member_id: int | None, flag_type: str, details: dict, severity: str = "MEDIUM") -> None:
    db.add(FraudFlag(member_id=member_id, flag_type=flag_type, severity=severity, details=details))


def register_member(db: Session, payload: dict) -> Member:
    normalized, valid = normalize_phone(payload.get("phone"))
    if not valid:
        raise HTTPException(status_code=422, detail="Enter a valid 10-digit Indian mobile number")
    if not str(payload.get("name", "")).strip():
        raise HTTPException(status_code=422, detail="Name is required")
    if db.execute(select(User.id).where(User.phone == normalized)).first():
        flag(db, None, "DUPLICATE_PHONE", {"phone": normalized, "attempted_name": payload.get("name")}, "HIGH")
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered")

    dob_result = parse_date(payload.get("date_of_birth"))
    if dob_result.value is None:
        raise HTTPException(status_code=422, detail=f"Invalid date of birth: {dob_result.warning or 'required'}")
    gender, gender_note = normalize_gender(payload.get("gender"))
    city, _ = normalize_city(payload.get("city"))
    income, _ = normalize_income(payload.get("income_range"))
    interests, _ = normalize_interests(payload.get("interests"))

    attribution = resolve_attribution(
        db, payload.get("source_token"), payload.get("how_heard"), payload.get("referral_token")
    )
    if attribution["errors"] and not attribution["source_id"] and not attribution["referrer_member_id"]:
        raise HTTPException(status_code=422, detail="; ".join(attribution["errors"]))

    source_id = attribution["source_id"]
    referrer_id = attribution["referrer_member_id"]
    if referrer_id and not source_id:
        source_id = ensure_source(db, "Referral", "REFERRAL").id

    user = User(phone=normalized, role="MEMBER")
    db.add(user)
    db.flush()
    member = Member(
        member_code=unique_member_code(db),
        user_id=user.id,
        name=str(payload["name"]).strip(),
        email=str(payload.get("email") or "").strip() or None,
        date_of_birth=dob_result.value,
        gender=gender,
        city=city,
        income_range=income,
        interests=interests,
        source_id=source_id,
        first_touch_source_id=source_id,
        referred_by_member_id=referrer_id if referrer_id and referrer_id != user.id else None,
        joined_at=datetime.now(timezone.utc),
        registration_ip=payload.get("registration_ip"),
        registration_device_hash=payload.get("registration_device_hash"),
    )
    db.add(member)
    db.flush()
    db.add(ReferralLink(token=unique_referral_token(db), member_id=member.id))

    touch_data = {
        "source_token": payload.get("source_token"),
        "how_heard": payload.get("how_heard"),
        "referral_token": payload.get("referral_token"),
        "gender_note": gender_note,
    }
    if source_id:
        db.add(
            AttributionHistory(
                member_id=member.id,
                source_id=source_id,
                token=payload.get("source_token"),
                attribution_type="SOURCE_LINK" if payload.get("source_token") else "QUESTIONNAIRE",
                touch="FIRST",
                raw_value=touch_data,
            )
        )
        db.add(
            AttributionHistory(
                member_id=member.id,
                source_id=source_id,
                token=payload.get("source_token"),
                attribution_type="SOURCE_LINK" if payload.get("source_token") else "QUESTIONNAIRE",
                touch="LAST",
                raw_value=touch_data,
            )
        )

    if referrer_id:
        referrer = db.get(Member, referrer_id)
        suspicious = referrer is None or referrer.user_id == user.id
        if not suspicious:
            ancestor = referrer.referred_by_member_id
            seen = {referrer_id}
            while ancestor and ancestor not in seen:
                if ancestor == member.id:
                    suspicious = True
                    break
                seen.add(ancestor)
                ancestor = db.get(Member, ancestor).referred_by_member_id if db.get(Member, ancestor) else None
        db.add(
            Referral(
                referrer_member_id=referrer_id,
                referred_member_id=member.id,
                status="FAILED" if suspicious else "LEAD",
                failure_reason="Self-referral or referral cycle detected" if suspicious else None,
            )
        )
        if suspicious:
            flag(db, member.id, "REFERRAL_CYCLE", {"referrer_member_id": referrer_id}, "HIGH")
        db.add(
            AttributionHistory(
                member_id=member.id,
                attribution_type="REFERRAL_LINK",
                touch="LAST",
                token=payload.get("referral_token"),
                raw_value={"referrer_member_id": referrer_id},
            )
        )

    db.commit()
    db.refresh(member)
    return member


def get_member_for_user(db: Session, user_id: int) -> Member | None:
    return db.execute(select(Member).where(Member.user_id == user_id)).scalars().first()


def update_profile(db: Session, member: Member, payload: dict) -> Member:
    allowed = ["name", "email", "gender", "city", "income_range", "interests", "date_of_birth"]
    for key in allowed:
        if key not in payload:
            continue
        value = payload[key]
        if key == "date_of_birth":
            parsed = parse_date(value)
            if parsed.value is None:
                raise HTTPException(status_code=422, detail=f"Invalid date of birth: {parsed.warning}")
            value = parsed.value
        elif key == "gender":
            value, note = normalize_gender(value)
            if value is None:
                raise HTTPException(status_code=422, detail=note)
        elif key == "city":
            value, _ = normalize_city(value)
        elif key == "income_range":
            value, _ = normalize_income(value)
        elif key == "interests":
            value, _ = normalize_interests(value)
        setattr(member, key, value)
    db.commit()
    db.refresh(member)

    from app.services.eligibility_service import recalculate_for_member

    recalculate_for_member(db, member.id)
    return member


def search_members(db: Session, *, search: str = "", source_id: int | None = None, city: str | None = None,
                   status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    query = select(Member)
    count = select(func.count(Member.id))
    conditions = []
    if search:
        term = f"%{search.strip()}%"
        conditions.append(or_(Member.name.ilike(term), Member.member_code.ilike(term), Member.city.ilike(term)))
    if source_id:
        conditions.append(Member.source_id == source_id)
    if city:
        conditions.append(Member.city.ilike(city))
    if status:
        conditions.append(Member.status == status.upper())
    for condition in conditions:
        query = query.where(condition)
        count = count.where(condition)
    total = db.execute(count).scalar_one()
    items = db.execute(
        query.order_by(Member.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size)}


def source_dashboard(db: Session) -> list[dict]:
    rows = db.execute(
        select(
            Source.id,
            Source.name,
            func.count(func.distinct(Member.id)).label("signups"),
            func.count(func.distinct(Referral.id)).filter(Referral.status.in_(["FIT", "COMPLETED"])).label("fit"),
            func.count(func.distinct(Referral.id)).filter(Referral.status == "COMPLETED").label("completed"),
        )
        .outerjoin(Member, Member.source_id == Source.id)
        .outerjoin(Referral, Referral.referrer_member_id == Member.id)
        .group_by(Source.id, Source.name)
        .order_by(Source.name)
    ).all()
    return [
        {"source_id": row.id, "source": row.name, "signups": row.signups, "fit": row.fit, "completed": row.completed}
        for row in rows
    ]
