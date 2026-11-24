"""Additive v2 models: questionnaire versions, responses and autosaved answers."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.member import Member
    from app.models.survey import Survey

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class QuestionnaireVersion(Base):
    __tablename__ = "questionnaire_versions"
    __table_args__ = (UniqueConstraint("survey_id", "version", name="uq_questionnaire_survey_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    raw_text: Mapped[str] = mapped_column(Text)
    ast: Mapped[dict] = mapped_column(JSON_TYPE)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["Survey"] = relationship(lazy="joined")


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    __table_args__ = (UniqueConstraint("survey_id", "member_id", name="uq_survey_member_response"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="IN_PROGRESS", index=True)
    answers: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    path: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    meta: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    member: Mapped["Member"] = relationship(lazy="joined")
    version: Mapped[QuestionnaireVersion] = relationship(lazy="joined")


class SurveyAnswer(Base):
    __tablename__ = "survey_answers"
    __table_args__ = (UniqueConstraint("response_id", "question_id", name="uq_response_question_answer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(ForeignKey("survey_responses.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(String(16))
    value: Mapped[dict] = mapped_column(JSON_TYPE)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped[SurveyResponse] = relationship(lazy="joined")
