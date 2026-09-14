from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def create_assessment_record(
    answers: Dict[str, Any],
    assessment_result: Dict[str, Any],
    recommendation_payload: Dict[str, Any],
    report_payload: Optional[Dict[str, Any]] = None,
    product_name: str = "AI Product Assessment",
    version: str = "1.1",
    assessment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an immutable snapshot of a completed assessment.

    The record stores the inputs and outputs required to revisit
    the assessment later without recalculating it.
    """
    created_at = datetime.now(timezone.utc).isoformat()

    record_id = assessment_id or f"assessment_{created_at}"

    overall_score = float(
        assessment_result.get("overall_score", 0.0)
    )

    overall_percentage = float(
        assessment_result.get("overall_percentage", 0.0)
    )

    recommendation = str(
        recommendation_payload.get(
            "recommendation",
            assessment_result.get("recommendation", "Not Ready"),
        )
    )

    confidence = str(
        recommendation_payload.get(
            "confidence",
            "Low",
        )
    )

    launch_blockers = assessment_result.get(
        "launch_blockers",
        [],
    )

    record = {
        "id": record_id,
        "created_at": created_at,
        "product_name": product_name,
        "version": version,
        "overall_score": overall_score,
        "overall_percentage": overall_percentage,
        "recommendation": recommendation,
        "confidence": confidence,
        "blocker_count": len(launch_blockers),
        "answers": deepcopy(answers),
        "assessment_result": deepcopy(assessment_result),
        "recommendation_payload": deepcopy(recommendation_payload),
        "report_payload": deepcopy(report_payload or {}),
    }

    return record


def save_assessment(
    history: List[Dict[str, Any]],
    assessment_record: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Add an assessment to history while preventing duplicate IDs.

    Newest assessments are returned first.
    """
    record_id = assessment_record.get("id")

    if record_id:
        existing_ids = {
            item.get("id")
            for item in history
        }

        if record_id in existing_ids:
            return deepcopy(history)

    updated_history = [
        deepcopy(assessment_record),
        *deepcopy(history),
    ]

    return updated_history


def get_assessment_history(
    history: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return a safe copy of assessment history."""
    return deepcopy(history)


def get_assessment_by_id(
    history: List[Dict[str, Any]],
    assessment_id: str,
) -> Optional[Dict[str, Any]]:
    """Return a single assessment snapshot by ID."""
    for record in history:
        if record.get("id") == assessment_id:
            return deepcopy(record)

    return None


def history_contains(
    history: List[Dict[str, Any]],
    assessment_id: str,
) -> bool:
    """Return whether history already contains the assessment ID."""
    return any(
        record.get("id") == assessment_id
        for record in history
    )