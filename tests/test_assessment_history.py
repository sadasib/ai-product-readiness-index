from __future__ import annotations

from app.utils.assessment_history import (
    create_assessment_record,
    get_assessment_by_id,
    get_assessment_history,
    history_contains,
    save_assessment,
)


def build_sample_assessment():
    answers = {
        "q1": "yes",
        "q2": "partial",
    }

    assessment_result = {
        "overall_score": 88.1,
        "overall_percentage": 88.1,
        "recommendation": "Ready for Beta",
        "launch_blockers": [
            {
                "gate_title": "AI Quality",
                "prompt": "Has escalation behavior been reviewed?",
            }
        ],
        "gate_results": [],
        "failed_questions": [],
    }

    recommendation_payload = {
        "recommendation": "Ready for Beta",
        "confidence": "Moderate",
        "top_missing_items": [
            "AI Quality — Has escalation behavior been reviewed?"
        ],
        "next_actions": [
            "Review and test escalation behavior for high-risk cases."
        ],
    }

    report_payload = {
        "product_name": "AI Product Assessment",
        "recommendation": "Ready for Beta",
        "readiness_score": 88.1,
        "readiness_max": 100.0,
        "grade": "A-",
        "confidence": "Moderate",
    }

    return (
        answers,
        assessment_result,
        recommendation_payload,
        report_payload,
    )


def test_create_assessment_record():
    (
        answers,
        assessment_result,
        recommendation_payload,
        report_payload,
    ) = build_sample_assessment()

    record = create_assessment_record(
        answers=answers,
        assessment_result=assessment_result,
        recommendation_payload=recommendation_payload,
        report_payload=report_payload,
        product_name="Retail Returns Assistant",
        version="1.1",
        assessment_id="assessment_1",
    )

    assert record["id"] == "assessment_1"
    assert record["product_name"] == "Retail Returns Assistant"
    assert record["version"] == "1.1"

    assert record["overall_score"] == 88.1
    assert record["overall_percentage"] == 88.1
    assert record["recommendation"] == "Ready for Beta"
    assert record["confidence"] == "Moderate"
    assert record["blocker_count"] == 1

    assert record["answers"] == answers
    assert record["assessment_result"] == assessment_result
    assert record["recommendation_payload"] == recommendation_payload
    assert record["report_payload"] == report_payload

    assert "created_at" in record


def test_create_assessment_record_creates_snapshot():
    answers = {
        "q1": "yes",
    }

    assessment_result = {
        "overall_score": 100.0,
        "overall_percentage": 100.0,
        "launch_blockers": [],
    }

    recommendation_payload = {
        "recommendation": "Ready for Production",
        "confidence": "High",
    }

    record = create_assessment_record(
        answers=answers,
        assessment_result=assessment_result,
        recommendation_payload=recommendation_payload,
        assessment_id="assessment_1",
    )

    answers["q1"] = "no"
    assessment_result["overall_score"] = 0.0

    assert record["answers"]["q1"] == "yes"
    assert record["assessment_result"]["overall_score"] == 100.0


def test_save_assessment_adds_new_record():
    record = {
        "id": "assessment_1",
        "overall_score": 88.1,
    }

    result = save_assessment(
        history=[],
        assessment_record=record,
    )

    assert len(result) == 1
    assert result[0]["id"] == "assessment_1"


def test_save_assessment_places_newest_first():
    existing = {
        "id": "assessment_1",
        "overall_score": 70.0,
    }

    new_record = {
        "id": "assessment_2",
        "overall_score": 88.1,
    }

    result = save_assessment(
        history=[existing],
        assessment_record=new_record,
    )

    assert [item["id"] for item in result] == [
        "assessment_2",
        "assessment_1",
    ]


def test_save_assessment_prevents_duplicate_id():
    existing = {
        "id": "assessment_1",
        "overall_score": 88.1,
    }

    duplicate = {
        "id": "assessment_1",
        "overall_score": 95.0,
    }

    result = save_assessment(
        history=[existing],
        assessment_record=duplicate,
    )

    assert len(result) == 1
    assert result[0]["overall_score"] == 88.1


def test_get_assessment_history_returns_copy():
    record = {
        "id": "assessment_1",
        "overall_score": 88.1,
    }

    history = [record]

    result = get_assessment_history(history)

    result[0]["overall_score"] = 50.0

    assert history[0]["overall_score"] == 88.1


def test_get_assessment_by_id_returns_record():
    history = [
        {
            "id": "assessment_2",
            "overall_score": 90.0,
        },
        {
            "id": "assessment_1",
            "overall_score": 88.1,
        },
    ]

    result = get_assessment_by_id(
        history,
        "assessment_1",
    )

    assert result is not None
    assert result["overall_score"] == 88.1


def test_get_assessment_by_id_returns_none_for_missing_record():
    result = get_assessment_by_id(
        history=[],
        assessment_id="does_not_exist",
    )

    assert result is None


def test_history_contains():
    history = [
        {"id": "assessment_1"},
        {"id": "assessment_2"},
    ]

    assert history_contains(
        history,
        "assessment_1",
    )

    assert not history_contains(
        history,
        "assessment_3",
    )