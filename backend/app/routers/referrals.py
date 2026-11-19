from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.schemas.ops import StageIn
from app.services import referral_service

router = APIRouter(prefix="/admin/referrals", tags=["admin referrals"])


@router.get("")
def list_all(status: str | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    referrals = referral_service.all_referrals(db, status)
    return [
        {
            "id": item.id,
            "referrer_member_id": item.referrer_member_id,
            "referred_member_id": item.referred_member_id,
            "referred_name": item.referred.name if item.referred else None,
            "status": item.status,
            "failure_reason": item.failure_reason,
            "updated_at": item.updated_at,
        }
        for item in referrals
    ]


@router.patch("/{referral_id}/stage")
def update_stage(referral_id: int, payload: StageIn, db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    referral = referral_service.update_stage(db, referral_id, payload.status, payload.failure_reason)
    return {"id": referral.id, "status": referral.status, "failure_reason": referral.failure_reason}
