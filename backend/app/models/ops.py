from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, default=0)
    corrected_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="PREVIEW")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportStagedRow(Base):
    __tablename__ = "import_staged_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_job_id: Mapped[int] = mapped_column(ForeignKey("import_jobs.id", ondelete="CASCADE"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    original_data: Mapped[dict] = mapped_column(JSON_TYPE)
    normalized_data: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    corrections: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    errors: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    action: Mapped[str] = mapped_column(String(16), default="IMPORT")  # IMPORT | SKIP | REVIEW
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportRowError(Base):
    __tablename__ = "import_row_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_job_id: Mapped[int] = mapped_column(ForeignKey("import_jobs.id", ondelete="CASCADE"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    original_data: Mapped[dict] = mapped_column(JSON_TYPE)
    error_code: Mapped[str] = mapped_column(String(48))
    error_message: Mapped[str] = mapped_column(Text)
    action_taken: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MetaLead(Base):
    __tablename__ = "meta_leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    meta_lead_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    form_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    page_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    adgroup_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ad_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lead_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON_TYPE)
    processing_status: Mapped[str] = mapped_column(String(16), default="PROCESSED", index=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PayoutLedger(Base):
    __tablename__ = "payout_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(16))  # SURVEY | REFERRAL
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
