from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.ops import MetaLead
from app.models.user import User
from app.schemas.ops import MetaLeadOut
from app.services import meta_service

router = APIRouter(tags=["meta leads"])


@router.post("/webhooks/meta/leads")
async def meta_lead(request: Request, db: Session = Depends(get_db)):
    """Mock Meta lead endpoint. Accepts a webhook envelope OR a merged lead payload."""
    try:
        payload = await request.json()
    except Exception:
        return {"result": "rejected", "reason": "Body must be valid JSON"}
    if not isinstance(payload, dict):
        return {"result": "rejected", "reason": "Body must be a JSON object"}
    return meta_service.process_lead(db, payload)


@router.get("/admin/meta-leads", response_model=list[MetaLeadOut])
def meta_leads(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return list(db.execute(select(MetaLead).order_by(MetaLead.id.desc())).scalars().all())
