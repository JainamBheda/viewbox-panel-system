"""All SQLAlchemy models, imported together so Alembic/migrations can discover them."""

from app.models.member import FraudFlag, Member, Referral
from app.models.ops import ImportJob, ImportRowError, ImportStagedRow, MetaLead, PayoutLedger
from app.models.source import AttributionHistory, ReferralLink, Source, SourceLink
from app.models.survey import Survey, SurveyApplication, SurveyCompletion, SurveyRule
from app.models.user import OtpChallenge, User

__all__ = [
    "AttributionHistory",
    "FraudFlag",
    "ImportJob",
    "ImportRowError",
    "ImportStagedRow",
    "Member",
    "MetaLead",
    "OtpChallenge",
    "PayoutLedger",
    "Referral",
    "ReferralLink",
    "Source",
    "SourceLink",
    "Survey",
    "SurveyApplication",
    "SurveyCompletion",
    "SurveyRule",
    "User",
]
