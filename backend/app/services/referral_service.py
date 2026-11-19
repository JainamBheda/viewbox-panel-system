from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.member import Member, Referral
from app.models.survey import SurveyCompletion
from app.services.payout_service import ensure_referral_payout
from app.utils.phones import mask_phone


def list_for_referrer(db: Session, member_id: int) -> list[dict]:
    referrals = db.execute(
        select(Referral).where(Referral.referrer_member_id == member_id).order_by(Referral.id.desc())
    ).scalars().all()
    results = []
    for referral in referrals:
        referred = referral.referred
        phone = None
        if referred and referred.user:
            phone = referred.user.phone
        results.append(
            {
                "id": referral.id,
                "referred_name": referred.name if referred else "Unknown member",
                "member_code": referred.member_code if referred else "—",
                "masked_phone": mask_phone(phone),
                "status": referral.status,
                "failure_reason": referral.failure_reason,
                "created_at": referral.created_at,
                "updated_at": referral.updated_at,
            }
        )
    return results


def update_stage(db: Session, referral_id: int, status_value: str, failure_reason: str | None) -> Referral:
    if status_value not in {"LEAD", "FIT", "COMPLETED", "FAILED"}:
        raise HTTPException(status_code=422, detail="Invalid referral stage")
    referral = db.get(Referral, referral_id)
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    if status_value == "COMPLETED":
        passed = db.execute(
            select(SurveyCompletion.id).where(
                SurveyCompletion.member_id == referral.referred_member_id,
                SurveyCompletion.quality_status == "PASSED",
            )
        ).first()
        if not passed:
            raise HTTPException(
                status_code=409, detail="Cannot complete referral without a PASSED survey completion"
            )
        ensure_referral_payout(db, referral)
    if status_value == "FAILED" and not failure_reason:
        raise HTTPException(status_code=422, detail="A failure reason is required when a referral fails")
    referral.status = status_value
    referral.failure_reason = failure_reason if status_value == "FAILED" else None
    referral.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(referral)
    return referral


def all_referrals(db: Session, status_filter: str | None = None) -> list[Referral]:
    query = select(Referral)
    if status_filter:
        query = query.where(Referral.status == status_filter.upper())
    return list(db.execute(query.order_by(Referral.id.desc())).scalars().all())
