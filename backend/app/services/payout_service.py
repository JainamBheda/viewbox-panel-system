from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.member import Referral
from app.models.survey import SurveyCompletion
from app.models.user import User
from app.models.ops import PayoutLedger

REFERRAL_REWARD = 50.00


def ensure_survey_payout(db: Session, member_id: int, completion: SurveyCompletion) -> PayoutLedger | None:
    existing = db.execute(
        select(PayoutLedger).where(
            PayoutLedger.source_type == "SURVEY", PayoutLedger.reference_id == completion.id
        )
    ).scalars().first()
    if existing:
        return existing
    entry = PayoutLedger(
        member_id=member_id,
        source_type="SURVEY",
        reference_id=completion.id,
        amount=completion.reward_amount or 0,
        status="PENDING",
    )
    db.add(entry)
    return entry


def ensure_referral_payout(db: Session, referral: Referral) -> PayoutLedger | None:
    existing = db.execute(
        select(PayoutLedger).where(
            PayoutLedger.source_type == "REFERRAL", PayoutLedger.reference_id == referral.id
        )
    ).scalars().first()
    if existing:
        return existing
    entry = PayoutLedger(
        member_id=referral.referrer_member_id,
        source_type="REFERRAL",
        reference_id=referral.id,
        amount=REFERRAL_REWARD,
        status="PENDING",
    )
    db.add(entry)
    return entry


def change_payout_status(db: Session, payout_id: int, status_value: str, admin_id: int) -> PayoutLedger:
    if status_value not in {"PENDING", "APPROVED", "PAID", "FAILED"}:
        raise HTTPException(status_code=422, detail="Invalid payout status")
    entry = db.get(PayoutLedger, payout_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Payout entry not found")
    if status_value == "PAID":
        admin = db.get(User, admin_id)
        if not admin or admin.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Only ADMIN may mark a payout as paid")
        if entry.status != "APPROVED":
            raise HTTPException(status_code=409, detail="Payout must be approved before it can be paid")
        entry.paid_at = datetime.now(timezone.utc)
    if status_value == "APPROVED":
        entry.approved_by = admin_id
    entry.status = status_value
    db.commit()
    db.refresh(entry)
    return entry
