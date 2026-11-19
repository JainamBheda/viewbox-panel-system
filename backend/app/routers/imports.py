from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.schemas.ops import ImportJobOut, PreviewOut
from app.services import import_service

router = APIRouter(prefix="/admin/imports", tags=["admin imports"])


@router.post("/upload", response_model=ImportJobOut)
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    content = await file.read()
    return import_service.analyse(db, file.filename or "upload.csv", content)


@router.get("", response_model=list[ImportJobOut])
def jobs(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return import_service.list_jobs(db)


@router.get("/{job_id}/preview", response_model=PreviewOut)
def preview(job_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return import_service.preview(db, job_id)


@router.post("/{job_id}/confirm", response_model=ImportJobOut)
def confirm(job_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return import_service.confirm(db, job_id, admin.id)


@router.get("/{job_id}/errors.csv")
def error_report(job_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    csv_text = import_service.error_report_csv(db, job_id)
    return Response(content=csv_text, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="import-{job_id}-errors.csv"'})
