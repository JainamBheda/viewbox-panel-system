from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin, require_full_admin
from app.models.user import User
from app.schemas.source import SourceIn, SourceLinkOut, SourceOut, SourceUpdate
from app.services import source_service

router = APIRouter(prefix="/admin/sources", tags=["admin sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return source_service.list_sources(db)


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceIn, db: Session = Depends(get_db), admin: User = Depends(require_full_admin)):
    return source_service.create_source(db, payload.model_dump())


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db),
                  admin: User = Depends(require_full_admin)):
    return source_service.update_source(db, source_id, payload.model_dump(exclude_unset=True))


@router.get("/links", response_model=list[SourceLinkOut])
def list_links(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return source_service.list_source_links(db)


@router.post("/{source_id}/links", response_model=SourceLinkOut, status_code=status.HTTP_201_CREATED)
def create_link(source_id: int, campaign_name: str | None = None, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    return source_service.create_source_link(db, source_id, campaign_name, admin.id)
