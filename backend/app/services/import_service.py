"""Robust CSV import: analyse -> stage -> preview -> confirm -> audit report."""

import csv
import hashlib
import io
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.member import FraudFlag, Member, Referral
from app.models.ops import ImportJob, ImportRowError, ImportStagedRow
from app.models.source import AttributionHistory, ReferralLink
from app.models.user import User
from app.services.auth_service import ensure_source
from app.utils.dates import parse_date
from app.utils.normalization import (
    normalize_city,
    normalize_gender,
    normalize_income,
    normalize_interests,
    normalize_source,
)
from app.utils.phones import normalize_phone
from app.utils.tokens import unique_member_code, unique_referral_token

REQUIRED_COLUMNS = ["member_id", "name", "phone", "date_of_birth", "gender", "city", "source"]
ALL_COLUMNS = REQUIRED_COLUMNS + [
    "email", "income_range", "interests", "referred_by", "joined_on", "last_survey_completed_on"
]


def _error(staged: dict, code: str, message: str, action: str = "ROW SKIPPED") -> None:
    staged["errors"].append({"code": code, "message": message, "action": action})


def _correction(staged: dict, message: str) -> None:
    if message:
        staged["corrections"].append(message)


def analyse(db: Session, filename: str, content: bytes) -> ImportJob:
    file_hash = hashlib.sha256(content).hexdigest()
    existing = db.execute(select(ImportJob).where(ImportJob.file_hash == file_hash)).scalars().first()
    if existing:
        return existing

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    headers = [header.strip() for header in (reader.fieldnames or [])]
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing_columns:
        raise HTTPException(status_code=422, detail=f"Missing required columns: {', '.join(missing_columns)}")

    rows = list(reader)
    known_ids = {str(row.get("member_id", "")).strip() for row in rows if str(row.get("member_id", "")).strip()}
    seen_ids: set[str] = set()
    seen_phones: set[str] = set()
    job = ImportJob(filename=filename, file_hash=file_hash, total_rows=len(rows), status="PREVIEW")
    db.add(job)
    db.flush()

    for index, raw in enumerate(rows, start=2):
        original = {key: ("" if value is None else str(value)) for key, value in raw.items() if key is not None}
        staged = {
            "row_number": index,
            "original_data": original,
            "normalized_data": {},
            "corrections": [],
            "errors": [],
            "action": "IMPORT",
        }
        if not any(str(value).strip() for value in original.values()):
            staged["action"] = "SKIP"
            _error(staged, "BLANK_ROW", "Entire row is blank", "ROW SKIPPED — no data invented")
            _persist_staged(db, job, staged)
            continue

        member_code = str(original.get("member_id", "")).strip().upper()
        if not member_code:
            staged["action"] = "SKIP"
            _error(staged, "MISSING_MEMBER_ID", "member_id is required", "ROW SKIPPED")
            _persist_staged(db, job, staged)
            continue
        if member_code in seen_ids:
            staged["action"] = "SKIP"
            _error(staged, "DUPLICATE_MEMBER_ID", f"member_id {member_code} already present in this file", "ROW SKIPPED — original retained in audit")
            _persist_staged(db, job, staged)
            continue
        seen_ids.add(member_code)

        name = " ".join(str(original.get("name", "")).split())
        if not name:
            staged["action"] = "SKIP"
            _error(staged, "MISSING_NAME", "name is required", "ROW SKIPPED")
            _persist_staged(db, job, staged)
            continue

        phone, phone_valid = normalize_phone(original.get("phone"))
        if not phone_valid:
            staged["action"] = "SKIP"
            _error(staged, "INVALID_PHONE", f"Invalid phone number '{original.get('phone')}'", "ROW SKIPPED")
            _persist_staged(db, job, staged)
            continue
        if phone in seen_phones:
            staged["action"] = "SKIP"
            _error(staged, "DUPLICATE_PHONE", f"Phone {phone} already used in this file", "ROW SKIPPED — flagged for review")
            db.add(FraudFlag(member_id=None, flag_type="DUPLICATE_PHONE", severity="HIGH",
                             details={"phone": phone, "row": index, "member_code": member_code}))
            _persist_staged(db, job, staged)
            continue
        seen_phones.add(phone)
        if str(original.get("phone", "")).strip() != phone:
            _correction(staged, f"Phone '{original.get('phone')}' normalized to '{phone}'")

        dob = parse_date(original.get("date_of_birth"))
        if dob.value is None:
            staged["action"] = "SKIP"
            _error(staged, "INVALID_DOB", dob.warning or "Invalid date of birth", "ROW SKIPPED")
            _persist_staged(db, job, staged)
            continue
        if dob.status == "AMBIGUOUS_DATE":
            _error(staged, "AMBIGUOUS_DATE", dob.warning or "Ambiguous date", "IMPORTED WITH WARNING")

        email = str(original.get("email", "")).strip() or None
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            _error(staged, "INVALID_EMAIL", f"Invalid email '{email}' — set to null; original preserved", "IMPORTED WITH WARNING")
            _correction(staged, f"Invalid email '{email}' not stored")
            email = None

        gender, gender_note = normalize_gender(original.get("gender"))
        _correction(staged, gender_note)
        if not gender:
            _error(staged, "UNKNOWN_GENDER", f"Unknown gender '{original.get('gender')}'", "IMPORTED WITH WARNING")
        city, city_note = normalize_city(original.get("city"))
        _correction(staged, city_note)
        if not city:
            _error(staged, "MISSING_CITY", "City is blank", "IMPORTED WITH WARNING")
        income, income_note = normalize_income(original.get("income_range"))
        _correction(staged, income_note)
        if not income:
            _error(staged, "UNKNOWN_INCOME", income_note or "Blank income range", "IMPORTED WITH WARNING")
        interests, interest_notes = normalize_interests(original.get("interests"))
        for note in interest_notes:
            _correction(staged, note)
        source_info, source_note = normalize_source(original.get("source"))
        _correction(staged, source_note)
        if not source_info:
            _error(staged, "UNKNOWN_SOURCE", source_note or "Blank source", "IMPORTED WITHOUT SOURCE")

        referred_by = str(original.get("referred_by", "")).strip().upper()
        if referred_by and referred_by not in known_ids:
            _error(staged, "UNKNOWN_REFERRAL_ID", f"Referrer '{referred_by}' not found in file", "NO REFERRAL CREATED")
            referred_by = None
        if referred_by and referred_by == member_code:
            _error(staged, "SELF_REFERRAL", "Member refers themselves", "NO REFERRAL CREATED — flagged")
            db.add(FraudFlag(member_id=None, flag_type="SELF_REFERRAL", severity="HIGH",
                             details={"row": index, "member_code": member_code}))
            referred_by = None

        joined = parse_date(original.get("joined_on"))
        if joined.value and joined.status == "AMBIGUOUS_DATE":
            _error(staged, "AMBIGUOUS_DATE", joined.warning or "Ambiguous joined_on", "IMPORTED WITH WARNING")
        completed = parse_date(original.get("last_survey_completed_on"))
        if completed.value and completed.status == "AMBIGUOUS_DATE":
            _error(staged, "AMBIGUOUS_DATE", completed.warning or "Ambiguous completion date", "IMPORTED WITH WARNING")

        staged["normalized_data"] = {
            "member_code": member_code,
            "name": name,
            "phone": phone,
            "email": email,
            "date_of_birth": dob.value.isoformat(),
            "gender": gender,
            "city": city,
            "income_range": income,
            "interests": interests,
            "source_name": source_info[0] if source_info else None,
            "source_type": source_info[1] if source_info else None,
            "referred_by_code": referred_by,
            "joined_at": joined.value.isoformat() if joined.value else None,
            "last_survey_completed_at": completed.value.isoformat() if completed.value else None,
        }
        if staged["errors"]:
            staged["action"] = "IMPORT" if staged["action"] == "IMPORT" else staged["action"]
        _persist_staged(db, job, staged)

    db.commit()
    db.refresh(job)
    return job


def _persist_staged(db: Session, job: ImportJob, staged: dict) -> None:
    db.add(ImportStagedRow(import_job_id=job.id, **staged))


def preview(db: Session, job_id: int) -> dict:
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    staged = db.execute(
        select(ImportStagedRow).where(ImportStagedRow.import_job_id == job_id).order_by(ImportStagedRow.row_number)
    ).scalars().all()
    return {
        "job": job,
        "summary": {
            "total_rows": job.total_rows,
            "valid_rows": sum(1 for row in staged if row.action == "IMPORT" and not row.errors),
            "needs_review": sum(1 for row in staged if row.action == "IMPORT" and row.errors),
            "skipped_rows": sum(1 for row in staged if row.action == "SKIP"),
            "corrections": sum(len(row.corrections or []) for row in staged),
        },
        "rows": staged,
    }


def confirm(db: Session, job_id: int, created_by: int | None) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status == "CONFIRMED":
        return job

    staged_rows = db.execute(
        select(ImportStagedRow).where(ImportStagedRow.import_job_id == job_id).order_by(ImportStagedRow.row_number)
    ).scalars().all()
    created: dict[str, Member] = {}
    phone_in_db = {row[0] for row in db.execute(select(User.phone)).all()}

    for staged in staged_rows:
        if staged.action != "IMPORT" or not staged.normalized_data:
            continue
        data = staged.normalized_data
        code = data["member_code"]
        if db.execute(select(Member.id).where(Member.member_code == code)).first():
            _log_error(db, job, staged, "DUPLICATE_MEMBER_ID", "Member code already exists", "ROW SKIPPED")
            job.skipped_rows += 1
            continue
        if data["phone"] in phone_in_db:
            _log_error(db, job, staged, "DUPLICATE_PHONE", "Phone already registered", "ROW SKIPPED — flagged")
            db.add(FraudFlag(member_id=None, flag_type="DUPLICATE_PHONE", severity="HIGH",
                             details={"phone": data["phone"], "member_code": code}))
            job.skipped_rows += 1
            continue

        try:
            with db.begin_nested():
                source_id = None
                if data.get("source_name"):
                    source = ensure_source(db, data["source_name"], data.get("source_type") or "OTHER")
                    source_id = source.id
                joined = datetime.fromisoformat(data["joined_at"]) if data.get("joined_at") else datetime.now(timezone.utc)
                if joined.tzinfo is None:
                    joined = joined.replace(tzinfo=timezone.utc)
                completed = datetime.fromisoformat(data["last_survey_completed_at"]) if data.get("last_survey_completed_at") else None
                if completed and completed.tzinfo is None:
                    completed = completed.replace(tzinfo=timezone.utc)
                dob = datetime.fromisoformat(data["date_of_birth"]).date()
                member = Member(
                    member_code=code,
                    name=data["name"],
                    email=data.get("email"),
                    date_of_birth=dob,
                    gender=data.get("gender"),
                    city=data.get("city"),
                    income_range=data.get("income_range"),
                    interests=data.get("interests"),
                    source_id=source_id,
                    first_touch_source_id=source_id,
                    joined_at=joined,
                    last_survey_completed_at=completed,
                    status="FLAGGED" if staged.errors else "ACTIVE",
                )
                db.add(member)
                db.flush()
                db.add(ReferralLink(token=unique_referral_token(db), member_id=member.id))
                if source_id:
                    db.add(AttributionHistory(
                        member_id=member.id, source_id=source_id, attribution_type="IMPORT", touch="FIRST",
                        raw_value={"original_source": staged.original_data.get("source")},
                    ))
                    db.add(AttributionHistory(
                        member_id=member.id, source_id=source_id, attribution_type="IMPORT", touch="LAST",
                        raw_value={"original_source": staged.original_data.get("source")},
                    ))
                created[code] = member
                phone_in_db.add(data["phone"])
        except Exception as exc:  # per-row isolation: one bad row must not lose the others
            _log_error(db, job, staged, "ROW_IMPORT_FAILED", str(exc)[:500], "ROW SKIPPED")
            job.skipped_rows += 1
            continue

        for error in staged.errors or []:
            _log_error(db, job, staged, error["code"], error["message"], error["action"])
        job.imported_rows += 1
        job.corrected_rows += len(staged.corrections or [])
        job.error_rows += len(staged.errors or [])

    for staged in staged_rows:
        data = staged.normalized_data or {}
        referrer_code = data.get("referred_by_code")
        if not referrer_code or referrer_code not in created:
            continue
        referred = created.get(data["member_code"])
        if not referred:
            continue
        db.add(Referral(
            referrer_member_id=created[referrer_code].id,
            referred_member_id=referred.id,
            status="LEAD",
        ))

    for staged in staged_rows:
        if staged.action == "SKIP":
            job.skipped_rows += 1
            for error in staged.errors or []:
                _log_error(db, job, staged, error["code"], error["message"], error["action"])

    job.status = "CONFIRMED"
    job.created_by = created_by
    db.commit()
    db.refresh(job)
    return job


def _log_error(db: Session, job: ImportJob, staged: ImportStagedRow, code: str, message: str, action: str) -> None:
    db.add(ImportRowError(
        import_job_id=job.id,
        row_number=staged.row_number,
        original_data=staged.original_data,
        error_code=code,
        error_message=message,
        action_taken=action,
    ))


def error_report_csv(db: Session, job_id: int) -> str:
    errors = db.execute(
        select(ImportRowError).where(ImportRowError.import_job_id == job_id).order_by(
            ImportRowError.row_number, ImportRowError.id
        )
    ).scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row_number", "error_code", "error_message", "action_taken", "original_data"])
    import json

    for error in errors:
        writer.writerow([
            error.row_number,
            error.error_code,
            error.error_message,
            error.action_taken,
            json.dumps(error.original_data, ensure_ascii=False),
        ])
    return output.getvalue()


def list_jobs(db: Session) -> list[ImportJob]:
    return list(db.execute(select(ImportJob).order_by(ImportJob.id.desc())).scalars().all())
