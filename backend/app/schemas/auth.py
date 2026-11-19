from pydantic import BaseModel, Field


class OtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=16)


class VerifyOtp(OtpRequest):
    otp: str = Field(min_length=4, max_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    member_id: int | None
    profile_complete: bool


class MeResponse(BaseModel):
    id: int
    phone: str
    role: str
    member_id: int | None
    profile_complete: bool
