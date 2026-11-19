from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MemberBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    date_of_birth: str
    gender: str
    city: str | None = None
    income_range: str | None = None
    interests: str | None = None
    email: EmailStr | None = None


class RegisterIn(MemberBase):
    phone: str
    source_token: str | None = None
    referral_token: str | None = None
    how_heard: str | None = None
    registration_ip: str | None = None
    registration_device_hash: str | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    city: str | None = None
    income_range: str | None = None
    interests: list[str] | str | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_code: str
    name: str
    email: str | None
    date_of_birth: date | None
    gender: str | None
    city: str | None
    income_range: str | None
    interests: list | None
    source_id: int | None
    first_touch_source_id: int | None
    referred_by_member_id: int | None
    joined_at: datetime
    last_survey_completed_at: datetime | None
    status: str


class MemberPage(BaseModel):
    items: list[MemberOut]
    total: int
    page: int
    page_size: int
    pages: int


class SourceStat(BaseModel):
    source_id: int
    source: str
    signups: int
    fit: int
    completed: int
