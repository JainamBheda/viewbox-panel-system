from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_member
from app.models.member import Member
from app.models.user import User
from app.schemas.member import MemberOut, ProfileUpdate
from app.schemas.ops import PayoutOut, ReferralOut
from app.schemas.survey import SurveyForMember
from app.services import eligibility_service, member_service, referral_service, source_service, survey_service

router = APIRouter(prefix="/members", tags=["member portal"])


def _my_member(user: User, db: Session) -> Member:
    member = member_service.get_member_for_user(db, user.id)
    if not member:
        raise HTTPException(status_code=404, detail="Member profile not found")
    return member


@router.get("/me", response_model=MemberOut)
def my_profile(user: User = Depends(require_member), db: Session = Depends(get_db)):
    return _my_member(user, db)


@router.put("/me/profile", response_model=MemberOut)
def update_profile(payload: ProfileUpdate, user: User = Depends(require_member), db: Session = Depends(get_db)):
    member = _my_member(user, db)
    return member_service.update_profile(db, member, payload.model_dump(exclude_unset=True))


@router.get("/me/referral-link")
def my_referral_link(user: User = Depends(require_member), db: Session = Depends(get_db)):
    member = _my_member(user, db)
    link = source_service.ensure_referral_link(db, member.id)
    return {"token": link.token, "url": f"/register?ref={link.token}"}


@router.get("/me/referrals", response_model=list[ReferralOut])
def my_referrals(user: User = Depends(require_member), db: Session = Depends(get_db)):
    return referral_service.list_for_referrer(db, _my_member(user, db).id)


@router.get("/me/surveys", response_model=list[SurveyForMember])
def my_surveys(user: User = Depends(require_member), db: Session = Depends(get_db)):
    member = _my_member(user, db)
    from app.services.eligibility_service import evaluate

    results = []
    for survey in survey_service.list_surveys(db, live_only=True):
        result = evaluate(db, survey, member)
        results.append({
            "survey": survey,
            "eligibility": {"status": result.status, "reason": result.reason, "rule_results": result.rule_results},
            "application_status": None,
        })
    return results


@router.post("/me/surveys/{survey_id}/apply")
def apply(survey_id: int, user: User = Depends(require_member), db: Session = Depends(get_db)):
    member = _my_member(user, db)
    survey = survey_service.get_survey(db, survey_id)
    application = eligibility_service.apply_to_survey(db, survey, member)
    return {"status": application.eligibility_status, "reason": application.reason}


@router.get("/me/payouts", response_model=list[PayoutOut])
def my_payouts(user: User = Depends(require_member), db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.models.ops import PayoutLedger

    member = _my_member(user, db)
    return list(db.execute(select(PayoutLedger).where(PayoutLedger.member_id == member.id)).scalars().all())
