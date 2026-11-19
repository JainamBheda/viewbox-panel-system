"""Phone normalization and privacy-safe display helpers."""

import re

INDIAN_MOBILE = re.compile(r"^[6-9]\d{9}$")


def normalize_phone(raw: str | None) -> tuple[str | None, bool]:
    """Strip formatting, remove country code / trunk zero, validate an Indian mobile.

    Returns (candidate, is_valid). Invalid candidates are returned unchanged when
    possible so the import preview can show what was found. Nothing is invented.
    """
    if raw is None:
        return None, False
    text = str(raw).strip()
    if not text:
        return None, False
    digits = re.sub(r"\D", "", text)
    if not digits:
        return text, False
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits, bool(INDIAN_MOBILE.fullmatch(digits))


def mask_phone(raw: str | None) -> str:
    """Return a privacy-safe phone for referrer dashboards."""
    normalized, valid = normalize_phone(raw)
    if not normalized:
        return "—"
    if not valid:
        return "•••••••••"
    return f"+91 {normalized[0]}•••• ••{normalized[-3:]}"
