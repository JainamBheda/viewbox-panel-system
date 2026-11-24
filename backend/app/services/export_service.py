"""CSV and XLSX export of the *currently filtered* respondent list."""

import io

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session

from app.services.member_service import search_members

HEADERS = [
    "member_id", "name", "phone", "email", "gender", "date_of_birth", "city",
    "income_range", "interests", "source", "referred_by", "joined_at", "status",
]

# Spreadsheet applications evaluate cells that begin with these characters.
# Escaping at export time keeps respondent-supplied text inert without changing stored data.
DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe(value) -> str:
    text = "" if value is None else str(value)
    if text and text[0] in DANGEROUS_PREFIXES:
        return "'" + text
    return text


def _rows(db: Session, search: str, source_id: int | None, city: str | None, status: str | None) -> list[list]:
    page = 1
    rows: list[list] = []
    while True:
        result = search_members(db, search=search, source_id=source_id, city=city, status=status,
                                page=page, page_size=500)
        for member in result["items"]:
            rows.append([_safe(value) for value in [
                member.member_code,
                member.name,
                member.user.phone if member.user else "",
                member.email or "",
                member.gender or "",
                member.date_of_birth.isoformat() if member.date_of_birth else "",
                member.city or "",
                member.income_range or "",
                "; ".join(member.interests or []) if isinstance(member.interests, list) else "",
                member.source.name if member.source else "",
                member.referred_by.member_code if member.referred_by else "",
                member.joined_at.isoformat() if member.joined_at else "",
                member.status,
            ]])
        if page >= result["pages"]:
            break
        page += 1
    return rows


def export_csv(db: Session, **filters) -> bytes:
    import csv

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADERS)
    writer.writerows(_rows(db, **filters))
    return "\ufeff".encode("utf-8") + buffer.getvalue().encode("utf-8")


def export_xlsx(db: Session, **filters) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Respondents"
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in _rows(db, **filters):
        sheet.append(row)
    for column in sheet.columns:
        width = max(len(str(cell.value or "")) for cell in column)
        sheet.column_dimensions[column[0].column_letter].width = min(max(width + 2, 10), 40)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
