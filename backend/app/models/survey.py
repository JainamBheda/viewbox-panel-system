from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.member import Member

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date] = mapped_column(Date)
    quota: Mapped[int] = mapped_column(Integer, default=100)
    reward_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    rules: Mapped[list["SurveyRule"]] = relationship(back_populates="survey", cascade="all, delete-orphan")
    applications: Mapped[list["SurveyApplication"]] = relationship(back_populates="survey", lazy="noload")


class SurveyRule(Base):
    __tablename__ = "survey_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    field_name: Mapped[str] = mapped_column(String(32))
    operator: Mapped[str] = mapped_column(String(16))
    expected_value: Mapped[str] = mapped_column(String(255))
    rule_type: Mapped[str] = mapped_column(String(16), default="STRICT")

    survey: Mapped[Survey] = relationship(back_populates="rules")


class SurveyApplication(Base):
    __tablename__ = "survey_applications"
    __table_args__ = (UniqueConstraint("survey_id", "member_id", name="uq_survey_member_application"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    eligibility_status: Mapped[str] = mapped_column(String(16), index=True)
    reason: Mapped[str] = mapped_column(Text)
    rule_results: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    survey: Mapped[Survey] = relationship(back_populates="applications", lazy="joined")
    member: Mapped["Member"] = relationship(lazy="joined")


class SurveyCompletion(Base):
    __tablename__ = "survey_completions"
    __table_args__ = (UniqueConstraint("survey_id", "member_id", name="uq_survey_member_completion"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    quality_status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    reward_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
