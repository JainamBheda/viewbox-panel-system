from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceIn(BaseModel):
    name: str
    source_type: str
    description: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    description: str | None = None
    is_active: bool | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    description: str | None
    is_active: bool


class SourceLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    token: str
    source_id: int
    campaign_name: str | None
    is_active: bool
    created_at: datetime


class AttributionOut(BaseModel):
    source_id: int | None
    source_name: str | None
    referrer_member_id: int | None
    referral_token: str | None
    errors: list[str]
