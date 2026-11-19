"""Safe, auditable normalization maps. Corrections are recorded, never silent."""

CITY_ALIASES = {
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "navi mumbai": "Navi Mumbai",
    "navimumbai": "Navi Mumbai",
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "pune": "Pune",
    "thane": "Thane",
    "ahmedabad": "Ahmedabad",
    "hyderabad": "Hyderabad",
    "delhi": "Delhi",
    "nagpur": "Nagpur",
    "nashik": "Nashik",
}

GENDER_ALIASES = {
    "m": "MALE", "male": "MALE",
    "f": "FEMALE", "female": "FEMALE",
    "other": "OTHER", "o": "OTHER",
}

INCOME_VALUES = {"Below 3L", "3L-6L", "6L-10L", "10L-20L", "Above 20L"}
INCOME_ALIASES = {
    "below 3l": "Below 3L", "0-3l": "Below 3L",
    "3l-6l": "3L-6L", "3-6l": "3L-6L",
    "6l-10l": "6L-10L", "6-10l": "6L-10L",
    "10l-20l": "10L-20L", "10-20l": "10L-20L",
    "above 20l": "Above 20L", "20l+": "Above 20L",
}

SOURCE_ALIASES = {
    "instagram": ("Instagram", "INSTAGRAM"),
    "insta": ("Instagram", "INSTAGRAM"),
    "ig": ("Instagram", "INSTAGRAM"),
    "facebook": ("Facebook", "FACEBOOK"),
    "fb": ("Facebook", "FACEBOOK"),
    "website": ("Website", "WEBSITE"),
    "referral": ("Referral", "REFERRAL"),
    "whatsapp group - mumbai": ("WhatsApp Group - Mumbai", "WHATSAPP_GROUP"),
    "whatsapp mumbai": ("WhatsApp Group - Mumbai", "WHATSAPP_GROUP"),
    "wa grp mumbai": ("WhatsApp Group - Mumbai", "WHATSAPP_GROUP"),
    "whatsapp group - pune": ("WhatsApp Group - Pune", "WHATSAPP_GROUP"),
    "staff dm - agent 01": ("Staff DM - Agent 01", "STAFF_DM"),
    "staff dm - agent 02": ("Staff DM - Agent 02", "STAFF_DM"),
    "meta ads": ("Meta Ads", "META_ADS"),
}

INTEREST_TOKENS = {
    "Auto", "Kids", "Home", "Travel", "Health", "Tech", "Fashion", "Beauty", "Food", "Finance"
}


def normalize_city(raw: str | None) -> tuple[str | None, str | None]:
    if raw is None or not str(raw).strip():
        return None, None
    original = str(raw)
    cleaned = " ".join(original.strip().split())
    canonical = CITY_ALIASES.get(cleaned.lower())
    if canonical is None:
        return cleaned, None
    return canonical, None if canonical == cleaned else f"City '{original}' normalized to '{canonical}'"


def normalize_gender(raw: str | None) -> tuple[str | None, str | None]:
    if raw is None or not str(raw).strip():
        return None, None
    original = str(raw)
    canonical = GENDER_ALIASES.get(original.strip().lower())
    if canonical is None:
        return None, f"Unknown gender '{original}'"
    return canonical, None if canonical == original.strip().upper() or canonical == original.strip().title().replace(" ", "") else f"Gender '{original}' normalized to '{canonical}'"


def normalize_income(raw: str | None) -> tuple[str | None, str | None]:
    if raw is None or not str(raw).strip():
        return None, None
    original = str(raw)
    key = " ".join(original.strip().lower().split())
    if key in INCOME_ALIASES:
        canonical = INCOME_ALIASES[key]
        return canonical, None if canonical == original.strip() else f"Income '{original}' normalized to '{canonical}'"
    return None, f"Unrecognized income range '{original}'"


def normalize_source(raw: str | None) -> tuple[tuple[str, str] | None, str | None]:
    if raw is None or not str(raw).strip():
        return None, None
    original = str(raw)
    key = " ".join(original.strip().lower().split())
    if key in SOURCE_ALIASES:
        canonical, source_type = SOURCE_ALIASES[key]
        return (canonical, source_type), None if canonical == original.strip() else f"Source '{original}' normalized to '{canonical}'"
    return None, f"Unknown source '{original}' — left unassigned for admin review"


def normalize_interests(raw: str | None) -> tuple[list[str] | None, list[str]]:
    if raw is None or not str(raw).strip():
        return None, []
    notes: list[str] = []
    tokens: list[str] = []
    original = str(raw)
    if "," in original and ";" not in original:
        notes.append("Interests split on ',' (expected ';')")
    for part in re_split(original):
        token = part.strip()
        if not token:
            continue
        canonical = next((known for known in INTEREST_TOKENS if known.lower() == token.lower()), None)
        if canonical is None:
            notes.append(f"Unknown interest '{token}' retained for review")
            tokens.append(token)
        elif canonical != token:
            notes.append(f"Interest '{token}' normalized to '{canonical}'")
            tokens.append(canonical)
        else:
            tokens.append(canonical)
    return list(dict.fromkeys(tokens)), notes


def re_split(value: str) -> list[str]:
    import re

    return re.split(r"[;,|]", value)
