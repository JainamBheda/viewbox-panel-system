from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RuleIn(BaseModel):
    field_name: str
    operator: str
    expected_value: str
    rule_type: str = "STRICT"


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_name: str
    operator: str
    expected_value: str
    rule_type: str


class SurveyIn(BaseModel):
    title: str
    description: str | None = None
    start_date: date | None = None
    deadline: date
    quota: int = 100
    reward_amount: float = 0
    status: str = "DRAFT"
    rules: list[RuleIn] = []


class SurveyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: date | None = None
    deadline: date | None = None
    quota: int | None = None
    reward_amount: float | None = None
    status: str | None = None
    rules: list[RuleIn] | None = None


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    start_date: date | None
    deadline: date
    quota: int
    reward_amount: float
    status: str
    rules: list[RuleOut] = []


class EligibilityOut(BaseModel):
    status: str
    reason: str
    rule_results: list[dict]


class SurveyForMember(BaseModel):
    survey: SurveyOut
    eligibility: EligibilityOut
    application_status: str | None
    has_questionnaire: bool = False


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    member_id: int
    eligibility_status: str
    reason: str
    applied_at: datetime


class CompletionIn(BaseModel):
    quality_status: str


class QuestionnaireTextIn(BaseModel):
    text: str


class QuestionnaireVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    version: int
    status: str
    question_count: int
    created_at: datetime


class AnswerIn(BaseModel):
    question_id: str | None = None
    value: Any


class RuntimeStepOut(BaseModel):
    response_id: int
    status: str
    version: int
    question: dict | None
    progress: float
    termination_reason: str | None
