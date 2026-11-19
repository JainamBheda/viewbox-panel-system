from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReferralOut(BaseModel):
    id: int
    referred_name: str
    member_code: str
    masked_phone: str
    status: str
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class StageIn(BaseModel):
    status: str
    failure_reason: str | None = None


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    total_rows: int
    imported_rows: int
    skipped_rows: int
    corrected_rows: int
    error_rows: int
    status: str
    created_at: datetime


class StagedRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    original_data: dict
    normalized_data: dict | None
    corrections: list | None
    errors: list | None
    action: str


class PreviewOut(BaseModel):
    job: ImportJobOut
    summary: dict
    rows: list[StagedRowOut]


class MetaLeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meta_lead_id: str
    form_id: str | None
    campaign_id: str | None
    ad_id: str | None
    processing_status: str
    failure_reason: str | None
    member_id: int | None
    created_at: datetime


class PayoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    source_type: str
    reference_id: int | None
    amount: float
    status: str
    approved_by: int | None
    paid_at: datetime | None
