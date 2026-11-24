"""Plain-text questionnaire parser, validator and immutable version publisher."""

from datetime import date
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.questionnaire import QuestionnaireVersion

QUESTION_TYPES = {"single", "multi", "rating", "nps", "text", "yesno", "date"}
OPERATORS = {"EQ", "NE", "IN", "CONTAINS", "GTE", "LTE"}
QUESTION_ID = re.compile(r"^Q\d+$")
RANGE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def _error(errors: list[dict], line: int, code: str, message: str) -> None:
    errors.append({"line": line, "code": code, "message": message})


def _condition(line: int, field: str, operator: str, value: str, errors: list[dict]) -> dict | None:
    field = field.strip().upper()
    operator = operator.strip().upper()
    if not QUESTION_ID.match(field):
        _error(errors, line, "INVALID_REFERENCE", f"Condition references unknown question id '{field}'.")
        return None
    if operator not in OPERATORS:
        _error(errors, line, "INVALID_OPERATOR", f"Unsupported condition operator '{operator}'.")
        return None
    if not value.strip():
        _error(errors, line, "MISSING_VALUE", "Condition is missing its comparison value.")
        return None
    return {"field": field, "operator": operator, "value": value.strip()}


def parse_questionnaire(raw_text: str) -> dict:
    """Parse a text questionnaire into an AST with line-numbered validation errors."""
    questions: list[dict] = []
    logic: list[dict] = []
    terminations: list[dict] = []
    quotas: list[dict] = []
    errors: list[dict] = []
    seen_ids: set[str] = set()

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]

        if QUESTION_ID.match(parts[0].upper()):
            question_id = parts[0].upper()
            if question_id in seen_ids:
                _error(errors, line_number, "DUPLICATE_QUESTION_ID", f"Question '{question_id}' is defined more than once.")
                continue
            if len(parts) < 3 or not parts[2]:
                _error(errors, line_number, "INVALID_QUESTION", "Expected Qn | type | text [| options/range].")
                continue
            question_type = parts[1].lower()
            if question_type not in QUESTION_TYPES:
                _error(errors, line_number, "INVALID_TYPE", f"Unsupported question type '{parts[1]}'.")
                continue

            question = {
                "id": question_id,
                "type": question_type,
                "text": parts[2],
                "options": [],
                "min": None,
                "max": None,
                "required": True,
                "line": line_number,
            }
            if question_type in {"single", "multi"}:
                options = [option for option in parts[3:] if option]
                if len(options) < 2:
                    _error(errors, line_number, "MISSING_OPTIONS", f"{question_id} needs at least two pipe-separated options.")
                question["options"] = options
            elif question_type == "yesno":
                question["options"] = ["Yes", "No"]
            elif question_type in {"rating", "nps"}:
                match = RANGE.match(parts[3]) if len(parts) > 3 else None
                if not match:
                    _error(errors, line_number, "MISSING_RANGE", f"{question_id} needs a range such as 1-5 or 0-10.")
                else:
                    question["min"] = int(match.group(1))
                    question["max"] = int(match.group(2))
                    if question["min"] >= question["max"]:
                        _error(errors, line_number, "INVALID_RANGE", f"{question_id} range must be ascending.")
            questions.append(question)
            seen_ids.add(question_id)
            continue

        directive = parts[0].upper()
        if directive in {"SHOW", "SKIP"}:
            if len(parts) != 6 or parts[2].upper() != "IF":
                _error(errors, line_number, "INVALID_DIRECTIVE", f"{directive} syntax is: {directive} | Qn | IF | Qx | OP | value.")
                continue
            condition = _condition(line_number, parts[3], parts[4], parts[5], errors)
            target = parts[1].upper()
            if condition:
                logic.append({"action": directive, "target": target, **condition, "line": line_number})
            continue

        if directive == "TERMINATE":
            if len(parts) < 6 or parts[1].upper() != "IF":
                _error(errors, line_number, "INVALID_DIRECTIVE", "TERMINATE syntax is: TERMINATE | IF | Qx | OP | value | reason.")
                continue
            condition = _condition(line_number, parts[2], parts[3], parts[4], errors)
            reason = " | ".join(parts[5:]).strip()
            if not reason:
                _error(errors, line_number, "MISSING_REASON", "TERMINATE requires a reason shown to the member.")
            if condition:
                terminations.append({**condition, "reason": reason, "line": line_number})
            continue

        if directive == "QUOTA":
            if len(parts) != 4:
                _error(errors, line_number, "INVALID_DIRECTIVE", "QUOTA syntax is: QUOTA | Qx | value | target.")
                continue
            target = parts[1].upper()
            try:
                quota_target = int(parts[3])
            except ValueError:
                _error(errors, line_number, "INVALID_QUOTA", "Quota target must be an integer.")
                continue
            if quota_target <= 0:
                _error(errors, line_number, "INVALID_QUOTA", "Quota target must be positive.")
                continue
            quotas.append({"field": target, "value": parts[2], "quota_target": quota_target, "line": line_number})
            continue

        _error(errors, line_number, "UNKNOWN_DIRECTIVE", f"Unrecognised questionnaire line: {raw_line[:80]}")

    if not questions:
        _error(errors, 1, "NO_QUESTIONS", "Questionnaire must define at least one question.")

    known_ids = {question["id"] for question in questions}
    question_by_id = {question["id"]: question for question in questions}
    for rule in logic + terminations + quotas:
        for field_key in ("target", "field"):
            reference = rule.get(field_key)
            if reference and reference not in known_ids:
                _error(errors, rule["line"], "INVALID_REFERENCE", f"References unknown question '{reference}'.")
        if "operator" in rule and "value" in rule and "field" in rule:
            options = question_by_id.get(rule["field"], {}).get("options", [])
            if options and rule["operator"] in {"EQ", "NE", "IN"} and rule["value"] not in options:
                _error(
                    errors,
                    rule["line"],
                    "UNKNOWN_OPTION",
                    f"'{rule['value']}' is not an option of {rule['field']}.",
                )

    for quota in quotas:
        options = question_by_id.get(quota["field"], {}).get("options", [])
        if options and quota["value"] not in options:
            _error(errors, quota["line"], "UNKNOWN_OPTION", f"Quota value '{quota['value']}' is not an option of {quota['field']}.")

    return {
        "questions": questions,
        "logic": logic,
        "terminations": terminations,
        "quotas": quotas,
        "errors": errors,
        "valid": not errors,
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def condition_matches(condition: dict, answers: dict) -> bool:
    value = answers.get(condition["field"])
    if value is None:
        return False
    values = [str(item).strip().lower() for item in _as_list(value)]
    expected = str(condition["value"]).strip()
    operator = condition["operator"]
    if operator == "EQ":
        return expected.strip().lower() in values
    if operator == "NE":
        return expected.strip().lower() not in values
    if operator == "IN":
        targets = {item.strip().lower() for item in expected.replace(";", ",").split(",")}
        return any(item in targets for item in values)
    if operator == "CONTAINS":
        needle = expected.strip().lower()
        return any(needle in item for item in values)
    try:
        numeric = float(values[0])
        target = float(expected)
    except (TypeError, ValueError):
        return False
    if operator == "GTE":
        return numeric >= target
    if operator == "LTE":
        return numeric <= target
    return False


def _is_hidden(question_id: str, ast: dict, answers: dict) -> bool:
    for rule in ast.get("logic", []):
        if rule.get("target") != question_id:
            continue
        matches = condition_matches(rule, answers)
        if rule["action"] == "SHOW" and not matches:
            return True
        if rule["action"] == "SKIP" and matches:
            return True
    return False


def _display_answer(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _render_question(question: dict, answers: dict) -> dict:
    text = question["text"]
    for question_id, answer in answers.items():
        text = text.replace("{" + question_id + "}", _display_answer(answer))
    return {
        "id": question["id"],
        "type": question["type"],
        "text": text,
        "options": question.get("options", []),
        "min": question.get("min"),
        "max": question.get("max"),
        "required": question.get("required", True),
    }


def next_question(ast: dict, answers: dict) -> tuple[dict | None, str | None]:
    """Return the next visible unanswered question, or a termination reason."""
    for rule in ast.get("terminations", []):
        if condition_matches(rule, answers):
            return None, rule["reason"]
    for question in ast.get("questions", []):
        if question["id"] in answers or _is_hidden(question["id"], ast, answers):
            continue
        return _render_question(question, answers), None
    return None, None


def validate_answer(question: dict, value: Any) -> Any:
    question_type = question["type"]
    if question_type in {"single", "yesno"}:
        if not isinstance(value, str) or value not in question["options"]:
            raise HTTPException(status_code=422, detail=f"{question['id']} requires one of: {', '.join(question['options'])}.")
        return value
    if question_type == "multi":
        if not isinstance(value, list) or not value or any(item not in question["options"] for item in value):
            raise HTTPException(status_code=422, detail=f"{question['id']} requires one or more valid options.")
        return value
    if question_type in {"rating", "nps"}:
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"{question['id']} requires a whole number.") from None
        if not question["min"] <= numeric <= question["max"]:
            raise HTTPException(status_code=422, detail=f"{question['id']} must be between {question['min']} and {question['max']}.")
        return numeric
    if question_type == "text":
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(status_code=422, detail=f"{question['id']} requires a text answer.")
        return value.strip()[:2000]
    if question_type == "date":
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{question['id']} requires an ISO date (YYYY-MM-DD).") from None
    raise HTTPException(status_code=422, detail=f"Unsupported question type: {question_type}")


def active_version(db: Session, survey_id: int) -> QuestionnaireVersion | None:
    return db.execute(
        select(QuestionnaireVersion).where(
            QuestionnaireVersion.survey_id == survey_id,
            QuestionnaireVersion.status == "ACTIVE",
        )
    ).scalars().first()


def has_active(db: Session, survey_id: int) -> bool:
    return active_version(db, survey_id) is not None


def get_version(db: Session, survey_id: int, version_id: int) -> QuestionnaireVersion:
    version = db.get(QuestionnaireVersion, version_id)
    if not version or version.survey_id != survey_id:
        raise HTTPException(status_code=404, detail="Questionnaire version not found")
    return version


def publish(db: Session, survey_id: int, raw_text: str, *, activate: bool = True) -> QuestionnaireVersion:
    parsed = parse_questionnaire(raw_text)
    if not parsed["valid"]:
        raise HTTPException(status_code=422, detail={"message": "Questionnaire validation failed", "errors": parsed["errors"]})
    current = db.execute(
        select(QuestionnaireVersion)
        .where(QuestionnaireVersion.survey_id == survey_id)
        .order_by(QuestionnaireVersion.version.desc())
    ).scalars().first()
    next_number = current.version + 1 if current else 1
    if activate:
        for older in db.execute(
            select(QuestionnaireVersion).where(
                QuestionnaireVersion.survey_id == survey_id,
                QuestionnaireVersion.status == "ACTIVE",
            )
        ).scalars().all():
            older.status = "ARCHIVED"
    version = QuestionnaireVersion(
        survey_id=survey_id,
        version=next_number,
        raw_text=raw_text,
        ast={key: value for key, value in parsed.items() if key not in {"errors", "valid"}},
        status="ACTIVE" if activate else "DRAFT",
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
