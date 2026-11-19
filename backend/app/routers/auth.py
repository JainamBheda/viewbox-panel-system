from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import MeResponse, OtpRequest, TokenResponse, VerifyOtp
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/request-otp")
def request_otp(payload: OtpRequest, db: Session = Depends(get_db)):
    """Mock OTP: returns the code on screen in non-production environments."""
    return auth_service.request_otp(db, payload.phone)


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(payload: VerifyOtp, db: Session = Depends(get_db)):
    return auth_service.verify_otp(db, payload.phone, payload.otp)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.member_service import get_member_for_user

    member = get_member_for_user(db, user.id)
    return {
        "id": user.id,
        "phone": user.phone,
        "role": user.role,
        "member_id": member.id if member else None,
        "profile_complete": bool(member and member.name != "(profile incomplete)"),
    }
