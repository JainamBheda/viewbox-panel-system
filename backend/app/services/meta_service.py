"""Mock Meta Lead Ads ingest, grounded in Meta's documented webhook + Graph API shape."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.ops import MetaLead
from app.models.source import AttributionHistory, ReferralLink
from app.models.user import User
from app.services.auth_service import ensure_source
from app.services.member_service import flag
from app.utils.dates import parse_date
from app.utils.normalization import normalize_city
from app.utils.phones import normalize_phone
from app.utils.tokens import unique_member_code, unique_referral_token

FIELD_ALIASES = {
    "full_name": {"full_name", "name", "full name"},
    "phone": {"phone", "phone_number", "phonenumber", "mobile", "telephone"},
    "city": {"city", "town", "location"},
    "email": {"email", "email_address"},
}


def extract_changes(payload: dict) -> list[dict]:
    """Support both the documented page webhook envelope and a merged lead object."""
    if "entry" in payload:
        changes: list[dict] = []
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                if change.get("field") == "leadgen" or "leadgen_id" in value:
                    changes.append(value)
        return changes
    return [payload]


def _fields_to_dict(field_data: list[dict]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in field_data or []:
        name = str(item.get("name", "")).strip().lower()
        values = item.get("values") or []
        value = str(values[0]).strip() if values else ""
        for canonical, aliases in FIELD_ALIASES.items():
            if name in aliases:
                result[canonical] = value
    return result


def _created_time(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value.isdigit():
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    if isinstance(value, str):
        parsed = parse_date(value[:10])
        if parsed.value:
            return datetime(parsed.value.year, parsed.value.month, parsed.value.day, tzinfo=timezone.utc)
    return None


def process_lead(db: Session, payload: dict) -> dict:
    changes = extract_changes(payload)
    if not changes:
        return {"result": "rejected", "reason": "No leadgen change found in payload", "meta_lead_id": None}

    outcomes = []
    for change in changes:
        lead_id = str(change.get("leadgen_id") or change.get("meta_lead_id") or change.get("id") or "").strip()
        if not lead_id:
            outcomes.append({"result": "rejected", "reason": "Missing leadgen_id", "meta_lead_id": None})
            continue

        if db.execute(select(MetaLead.id).where(MetaLead.meta_lead_id == lead_id)).first():
            outcomes.append({"result": "already_processed", "meta_lead_id": lead_id})
            continue

        fields = _fields_to_dict(change.get("field_data") or [])
        name = fields.get("full_name") or str(change.get("name") or "").strip()
        phone, valid = normalize_phone(fields.get("phone") or change.get("phone"))
        city, _ = normalize_city(fields.get("city") or change.get("city"))
        email = fields.get("email") or change.get("email")

        problems = []
        if not name:
            problems.append("missing name")
        if not valid:
            problems.append("invalid or missing phone")

        lead = MetaLead(
            meta_lead_id=lead_id,
            form_id=str(change.get("form_id") or "") or None,
            page_id=str(change.get("page_id") or "") or None,
            campaign_id=str(change.get("campaign_id") or "") or None,
            adgroup_id=str(change.get("adgroup_id") or "") or None,
            ad_id=str(change.get("ad_id") or "") or None,
            lead_created_at=_created_time(change.get("created_time")),
            raw_payload=payload,
            processing_status="FLAGGED" if problems else "PROCESSED",
            failure_reason="; ".join(problems) if problems else None,
        )
        if problems:
            db.add(lead)
            db.flush()
            outcomes.append({"result": "flagged", "meta_lead_id": lead_id, "reason": "; ".join(problems)})
            continue

        if db.execute(select(User.id).where(User.phone == phone)).first():
            flag(db, None, "DUPLICATE_PHONE", {"phone": phone, "source": "Meta Ads"}, "HIGH")
            lead.processing_status = "FLAGGED"
            lead.failure_reason = "phone already registered"
            db.add(lead)
            db.flush()
            outcomes.append({"result": "flagged", "meta_lead_id": lead_id, "reason": "phone already registered"})
            continue

        source = ensure_source(db, "Meta Ads", "META_ADS")
        user = User(phone=phone, role="MEMBER")
        db.add(user)
        db.flush()
        member = Member(
            member_code=unique_member_code(db),
            user_id=user.id,
            name=name,
            email=email or None,
            city=city,
            source_id=source.id,
            first_touch_source_id=source.id,
            joined_at=lead.lead_created_at or datetime.now(timezone.utc),
        )
        db.add(member)
        db.flush()
        db.add(ReferralLink(token=unique_referral_token(db), member_id=member.id))
        db.add(
            AttributionHistory(
                member_id=member.id,
                source_id=source.id,
                attribution_type="META_LEAD",
                touch="FIRST",
                raw_value={"meta_lead_id": lead_id},
            )
        )
        db.add(
            AttributionHistory(
                member_id=member.id,
                source_id=source.id,
                attribution_type="META_LEAD",
                touch="LAST",
                raw_value={"meta_lead_id": lead_id, "campaign_id": lead.campaign_id, "ad_id": lead.ad_id},
            )
        )
        lead.member_id = member.id
        db.add(lead)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            outcomes.append({"result": "already_processed", "meta_lead_id": lead_id})
            continue
        outcomes.append(
            {"result": "created", "meta_lead_id": lead_id, "member_code": member.member_code, "campaign_id": lead.campaign_id}
        )

    db.commit()
    return outcomes[0] if len(outcomes) == 1 else {"result": "processed", "leads": outcomes}
