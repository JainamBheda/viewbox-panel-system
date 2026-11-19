from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source import ReferralLink, Source, SourceLink
from app.utils.tokens import unique_referral_token, unique_source_token

SOURCE_TYPES = {"WHATSAPP_GROUP", "STAFF_DM", "INSTAGRAM", "FACEBOOK", "WEBSITE", "REFERRAL", "META_ADS", "OTHER"}


def list_sources(db: Session, active_only: bool = False) -> list[Source]:
    query = select(Source)
    if active_only:
        query = query.where(Source.is_active.is_(True))
    return list(db.execute(query.order_by(Source.name)).scalars().all())


def create_source(db: Session, data: dict) -> Source:
    if data.get("source_type") not in SOURCE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid source_type")
    if db.execute(select(Source.id).where(Source.name.ilike(data["name"].strip()))).first():
        raise HTTPException(status_code=409, detail="Source name already exists")
    source = Source(**data, name=data["name"].strip(), is_active=True)
    db.add(source)
    db.flush()
    db.add(SourceLink(token=unique_source_token(db), source_id=source.id, campaign_name="Default link"))
    db.commit()
    db.refresh(source)
    return source


def update_source(db: Session, source_id: int, data: dict) -> Source:
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for key, value in data.items():
        if value is not None:
            setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


def create_source_link(db: Session, source_id: int, campaign_name: str | None, created_by: int) -> SourceLink:
    if not db.get(Source, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    link = SourceLink(
        token=unique_source_token(db), source_id=source_id, campaign_name=campaign_name, created_by=created_by
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def list_source_links(db: Session) -> list[SourceLink]:
    return list(db.execute(select(SourceLink).order_by(SourceLink.id.desc())).scalars().all())


def ensure_referral_link(db: Session, member_id: int) -> ReferralLink:
    link = db.execute(select(ReferralLink).where(ReferralLink.member_id == member_id)).scalars().first()
    if not link:
        link = ReferralLink(token=unique_referral_token(db), member_id=member_id)
        db.add(link)
        db.commit()
        db.refresh(link)
    return link
