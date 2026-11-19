from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.member import MemberOut, RegisterIn
from app.schemas.source import AttributionOut
from app.services import auth_service, member_service, source_service

router = APIRouter(prefix="/public", tags=["public registration"])


@router.get("/sources", response_model=list[dict])
def public_sources(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "source_type": s.source_type} for s in source_service.list_sources(db, True)]


@router.get("/attribution/resolve", response_model=AttributionOut)
def resolve(token: str | None = None, referral_token: str | None = None, how_heard: str | None = None,
            db: Session = Depends(get_db)):
    return auth_service.resolve_attribution(db, token or referral_token, how_heard, referral_token)


@router.post("/register", response_model=MemberOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data.get("interests") is not None and not isinstance(data["interests"], str):
        data["interests"] = "; ".join(data["interests"])
    return member_service.register_member(db, data)
