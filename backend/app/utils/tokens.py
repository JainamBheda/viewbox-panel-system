import secrets
import string
from sqlalchemy.orm import Session

from app.models.source import ReferralLink, SourceLink

ALPHABET = string.ascii_uppercase + string.digits


def generate_token(prefix: str, length: int = 12) -> str:
    return f"{prefix}-" + "".join(secrets.choice(ALPHABET) for _ in range(length))


def unique_source_token(db: Session) -> str:
    token = generate_token("SRC")
    while db.query(SourceLink.id).filter(SourceLink.token == token).first():
        token = generate_token("SRC")
    return token


def unique_referral_token(db: Session) -> str:
    token = generate_token("REF")
    while db.query(ReferralLink.id).filter(ReferralLink.token == token).first():
        token = generate_token("REF")
    return token


def unique_member_code(db: Session) -> str:
    """Generate a fresh code, skipping codes already consumed by imported rows."""
    from app.models.member import Member

    while True:
        code = f"VB{secrets.randbelow(900000) + 100000}"
        if not db.query(Member.id).filter(Member.member_code == code).first():
            return code
