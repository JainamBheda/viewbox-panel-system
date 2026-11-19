from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint("referred_by_member_id IS NULL OR referred_by_member_id <> id", name="ck_no_self_referral"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    member_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    income_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    interests: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True)
    first_touch_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True
    )
    referred_by_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL"), nullable=True, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_survey_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_device_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User | None"] = relationship("User", lazy="joined")
    source: Mapped["Source | None"] = relationship("Source", foreign_keys=[source_id], lazy="joined")
    first_touch_source: Mapped["Source | None"] = relationship(
        "Source", foreign_keys=[first_touch_source_id], lazy="noload"
    )
    referred_by: Mapped["Member | None"] = relationship("Member", remote_side=[id], lazy="noload")
    referral_link: Mapped["ReferralLink | None"] = relationship("ReferralLink", lazy="noload")


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        CheckConstraint("referrer_member_id <> referred_member_id", name="ck_referral_not_self"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), index=True
    )
    referred_member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="LEAD", index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    referrer: Mapped[Member] = relationship("Member", foreign_keys=[referrer_member_id], lazy="joined")
    referred: Mapped[Member] = relationship("Member", foreign_keys=[referred_member_id], lazy="joined")


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=True, index=True)
    flag_type: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    details: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
