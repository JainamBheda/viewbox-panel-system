from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin, require_full_admin
from app.models.user import User
from app.schemas.member import MemberPage, SourceStat
from app.schemas.ops import PayoutOut
from app.services import export_service, member_service, payout_service

router = APIRouter(prefix="/admin", tags=["admin dashboard"])


@router.get("/dashboard/sources", response_model=list[SourceStat])
def source_dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return member_service.source_dashboard(db)


@router.get("/members", response_model=MemberPage)
def members(search: str = "", source_id: int | None = None, city: str | None = None, status: str | None = None,
            page: int = 1, page_size: int = 20, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return member_service.search_members(
        db, search=search, source_id=source_id, city=city, status=status, page=max(page, 1), page_size=min(page_size, 200)
    )


@router.get("/members/export")
def export(format: str = "csv", search: str = "", source_id: int | None = None, city: str | None = None,
           status: str | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    filters = {"search": search, "source_id": source_id, "city": city, "status": status}
    if format == "xlsx":
        content = export_service.export_xlsx(db, **filters)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="viewbox-respondents.xlsx"'},
        )
    content = export_service.export_csv(db, **filters)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="viewbox-respondents.csv"'},
    )


@router.get("/fraud-flags")
def fraud_flags(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    from sqlalchemy import select
    from app.models.member import FraudFlag

    return list(db.execute(select(FraudFlag).order_by(FraudFlag.id.desc()).limit(200)).scalars().all())


@router.get("/payouts", response_model=list[PayoutOut])
def payouts(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    from sqlalchemy import select
    from app.models.ops import PayoutLedger

    return list(db.execute(select(PayoutLedger).order_by(PayoutLedger.id.desc())).scalars().all())


@router.patch("/payouts/{payout_id}", response_model=PayoutOut)
def change_payout(payout_id: int, status_value: str, db: Session = Depends(get_db),
                  admin: User = Depends(require_full_admin)):
    return payout_service.change_payout_status(db, payout_id, status_value, admin.id)
