"""Calendar arithmetic and deterministic date parsing for the CSV importer."""

from dataclasses import dataclass
from datetime import date, datetime
import re

ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
DMY = re.compile(r"^(\d{1,2})([/\-])(\d{1,2})\2(\d{2}|\d{4})$")
CENTURY_PIVOT = 26  # two-digit years <= 26 -> 20xx, otherwise 19xx


@dataclass
class ParsedDate:
    value: date | None
    status: str  # OK | AMBIGUOUS_DATE | INVALID_DATE | BLANK | UNKNOWN_FORMAT
    warning: str | None = None


def add_calendar_months(day: date, months: int) -> date:
    """Add calendar months, clamping the day to the last day of the target month."""
    total = day.month - 1 + months
    year = day.year + total // 12
    month = total % 12 + 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    last_day = (date(next_year, next_month, 1) - date.resolution).day
    return date(year, month, min(day.day, last_day))


def parse_date(value: object) -> ParsedDate:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return ParsedDate(None, "BLANK")

    match = ISO.fullmatch(raw)
    if match:
        try:
            return ParsedDate(date(*(int(part) for part in match.groups())), "OK")
        except ValueError:
            return ParsedDate(None, "INVALID_DATE", f"Invalid ISO date '{raw}'")

    match = DMY.fullmatch(raw)
    if match:
        day, month, year_text = int(match[1]), int(match[3]), match[4]
        year = int(year_text)
        if len(year_text) == 2:
            year += 2000 if year <= CENTURY_PIVOT else 1900
        ambiguous = day <= 12 and month <= 12 and day != month
        try:
            parsed = date(year, month, day)
        except ValueError:
            return ParsedDate(None, "INVALID_DATE", f"Invalid calendar date '{raw}'")
        if ambiguous:
            return ParsedDate(
                parsed,
                "AMBIGUOUS_DATE",
                f"Ambiguous date '{raw}' interpreted day-first as {parsed.isoformat()}; confirm manually",
            )
        return ParsedDate(parsed, "OK")

    return ParsedDate(None, "UNKNOWN_FORMAT", f"Unrecognised date format '{raw}'")


def display_date(day: date | datetime | None) -> str:
    if isinstance(day, datetime):
        day = day.date()
    return day.strftime("%d-%m-%Y") if day else "—"
