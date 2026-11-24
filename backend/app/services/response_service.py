"""Authenticated member questionnaire runtime and analytics."""

from datetime import datetime, timezone
from statistics import median
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.questionnaire import QuestionnaireVersion, SurveyAnswer, SurveyResponse
from app.models.survey import Survey, SurveyApplication
from app.services import questionnaire_service, survey_service


def _current_response(db: Session, survey_id: int, member_id: int) -> SurveyResponse | None:
    return db.execute(
        select(SurveyResponse).where(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.member_id == member_id,
        )
    ).scalars().first()


def _progress(ast: dict, answers: dict) -> float:
    total = len(ast.get("questions", []))
    if not total:
        return 0.0
    return round(100 * len(answers) / total, 1)


def _step(response: SurveyResponse) -> dict:
    ast = response.version.ast
    question, reason = questionnaire_service.next_question(ast, response.answers)
    return {
        "response_id": response.id,
        "status": response.status,
        "version": response.version.version,
        "question": question,
        "progress": _progress(ast, response.answers),
        "termination_reason": response.termination_reason or reason,
    }


def _terminate(db: Session, response: SurveyResponse, reason: str) -> None:
    response.status = "TERMINATED"
    response.termination_reason = reason
    response.completed_at = datetime.now(timezone.utc)


def _complete(db: Session, response: SurveyResponse, survey: Survey) -> None:
    db.execute(select(Survey.id).where(Survey.id == survey.id).with_for_update())
    completed = db.execute(
        select(func.count(SurveyResponse.id)).where(
            SurveyResponse.survey_id == survey.id,
            SurveyResponse.status == "COMPLETED",
        )
    ).scalar() or 0
    if completed >= survey.quota:
        _terminate(db, response, "Survey quota filled before this response was submitted.")
        return
    response.status = "COMPLETED"
    response.completed_at = datetime.now(timezone.utc)
    db.commit()
    survey_service.record_completion(db, survey.id, response.member_id, "PASSED")


def start_or_resume(db: Session, survey_id: int, member_id: int) -> dict:
    survey = survey_service.get_survey(db, survey_id)
    existing = _current_response(db, survey_id, member_id)
    if existing:
        return _step(existing)

    application = db.execute(
        select(SurveyApplication).where(
            SurveyApplication.survey_id == survey_id,
            SurveyApplication.member_id == member_id,
        )
    ).scalars().first()
    if not application or application.eligibility_status != "APPROVED":
        raise HTTPException(status_code=403, detail="An APPROVED application is required to start this questionnaire.")

    version = questionnaire_service.active_version(db, survey_id)
    if not version:
        raise HTTPException(status_code=404, detail="No active questionnaire is published for this survey.")

    db.execute(select(Survey.id).where(Survey.id == survey.id).with_for_update())
    completed = db.execute(
        select(func.count(SurveyResponse.id)).where(
            SurveyResponse.survey_id == survey.id,
            SurveyResponse.status == "COMPLETED",
        )
    ).scalar() or 0
    if completed >= survey.quota:
        raise HTTPException(status_code=409, detail="Survey quota is full.")

    response = SurveyResponse(
        survey_id=survey_id,
        member_id=member_id,
        version_id=version.id,
        answers={},
        path=[],
        meta={"rotation_arm": "A" if completed % 2 == 0 else "B"},
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return _step(response)


def current(db: Session, survey_id: int, member_id: int) -> dict:
    response = _current_response(db, survey_id, member_id)
    if not response:
        raise HTTPException(status_code=404, detail="Questionnaire response not started")
    return _step(response)


def submit_answer(db: Session, survey_id: int, member_id: int, question_id: str | None, value: Any) -> dict:
    response = _current_response(db, survey_id, member_id)
    if not response:
        raise HTTPException(status_code=404, detail="Questionnaire response not started")
    if response.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail=f"Response is already {response.status}.")

    question, reason = questionnaire_service.next_question(response.version.ast, response.answers)
    if reason:
        _terminate(db, response, reason)
        db.commit()
        return _step(response)
    if not question:
        return _step(response)
    if question_id and question_id != question["id"]:
        raise HTTPException(status_code=409, detail=f"Expected answer for {question['id']}.")

    normalized = questionnaire_service.validate_answer(question, value)
    response.answers = {**response.answers, question["id"]: normalized}
    response.path = [*response.path, question["id"]]
    db.add(
        SurveyAnswer(
            response_id=response.id,
            question_id=question["id"],
            value={"value": normalized},
        )
    )

    next_question, termination_reason = questionnaire_service.next_question(response.version.ast, response.answers)
    if termination_reason:
        _terminate(db, response, termination_reason)
        db.commit()
    elif next_question is None:
        survey = survey_service.get_survey(db, survey_id)
        db.commit()
        _complete(db, response, survey)
    else:
        db.commit()
    db.refresh(response)
    return _step(response)


def go_back(db: Session, survey_id: int, member_id: int) -> dict:
    response = _current_response(db, survey_id, member_id)
    if not response:
        raise HTTPException(status_code=404, detail="Questionnaire response not started")
    if response.status != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail=f"Response is already {response.status}.")
    if not response.path:
        return _step(response)

    last_id = response.path[-1]
    answers = dict(response.answers)
    answers.pop(last_id, None)
    response.answers = answers
    response.path = list(response.path[:-1])
    for answer in db.execute(
        select(SurveyAnswer).where(
            SurveyAnswer.response_id == response.id,
            SurveyAnswer.question_id == last_id,
        )
    ).scalars().all():
        db.delete(answer)
    db.commit()
    db.refresh(response)
    return _step(response)


def analytics(db: Session, survey_id: int) -> dict:
    survey_service.get_survey(db, survey_id)
    responses = db.execute(
        select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
    ).scalars().all()
    version = questionnaire_service.active_version(db, survey_id)
    ast = version.ast if version else {"questions": [], "terminations": []}

    question_stats = []
    for question in ast.get("questions", []):
        reached = sum(1 for response in responses if question["id"] in response.path)
        answered = sum(1 for response in responses if question["id"] in response.answers)
        question_stats.append({
            "id": question["id"],
            "text": question["text"],
            "reached": reached,
            "answered": answered,
            "dropoff": reached - answered,
        })

    terminations: dict[str, int] = {}
    for response in responses:
        if response.status == "TERMINATED" and response.termination_reason:
            terminations[response.termination_reason] = terminations.get(response.termination_reason, 0) + 1

    durations = []
    for response in responses:
        if response.status == "COMPLETED" and response.completed_at and response.started_at:
            durations.append(max((response.completed_at - response.started_at).total_seconds(), 0))
    speeders = 0
    if len(durations) >= 5:
        cutoff = median(durations) / 3
        speeders = sum(1 for duration in durations if duration < cutoff)

    return {
        "survey_id": survey_id,
        "active_version": version.version if version else None,
        "started": len(responses),
        "completed": sum(1 for response in responses if response.status == "COMPLETED"),
        "in_progress": sum(1 for response in responses if response.status == "IN_PROGRESS"),
        "terminated": sum(1 for response in responses if response.status == "TERMINATED"),
        "questions": question_stats,
        "termination_reasons": [
            {"reason": reason, "count": count} for reason, count in sorted(terminations.items())
        ],
        "quality_flags": {"speeders": speeders, "minimum_completes_for_speeder_check": 5},
    }
