from __future__ import annotations

from app.utils.recommendations import (
    build_next_actions,
    build_recommendation_payload,
    build_top_missing_items,
    recommend_launch_state,
)


def test_recommend_launch_state_production_without_blockers():
    result = recommend_launch_state(
        overall_score=95,
        launch_blockers=[],
    )

    assert result == {
        "recommendation": "Ready for Production",
        "confidence": "High",
    }


def test_recommend_launch_state_beta_without_blockers():
    result = recommend_launch_state(
        overall_score=82,
        launch_blockers=[],
    )

    assert result == {
        "recommendation": "Ready for Beta",
        "confidence": "High",
    }


def test_recommend_launch_state_with_high_score_and_blocker():
    blockers = [
        {
            "gate_title": "AI Quality",
            "prompt": "Has escalation behavior been reviewed?",
        }
    ]

    result = recommend_launch_state(
        overall_score=95,
        launch_blockers=blockers,
    )

    assert result == {
        "recommendation": "Ready for Beta",
        "confidence": "High",
    }


def test_recommend_launch_state_with_mid_score_and_blocker():
    blockers = [
        {
            "gate_title": "Trust & Safety",
            "prompt": "Has the bias review been completed?",
        }
    ]

    result = recommend_launch_state(
        overall_score=68,
        launch_blockers=blockers,
    )

    assert result == {
        "recommendation": "Additional Review Required",
        "confidence": "Moderate",
    }


def test_recommend_launch_state_low_score():
    result = recommend_launch_state(
        overall_score=45,
        launch_blockers=[],
    )

    assert result == {
        "recommendation": "Not Ready",
        "confidence": "Low",
    }


def test_build_top_missing_items_prioritizes_blockers():
    blockers = [
        {
            "gate_title": "AI Quality",
            "prompt": "Critical question",
        }
    ]

    failed_questions = [
        {
            "gate_title": "Customer Value",
            "prompt": "Non-critical question",
        }
    ]

    result = build_top_missing_items(
        launch_blockers=blockers,
        failed_questions=failed_questions,
    )

    assert result == [
        "AI Quality — Critical question",
        "Non-critical question",
    ]


def test_build_top_missing_items_removes_duplicates():
    blockers = [
        {
            "gate_title": "AI Quality",
            "prompt": "Review escalation",
        },
        {
            "gate_title": "AI Quality",
            "prompt": "Review escalation",
        },
    ]

    result = build_top_missing_items(
        launch_blockers=blockers,
        failed_questions=[],
    )

    assert result == [
        "AI Quality — Review escalation",
    ]


def test_build_top_missing_items_respects_limit():
    failed_questions = [
        {"prompt": "Question 1"},
        {"prompt": "Question 2"},
        {"prompt": "Question 3"},
    ]

    result = build_top_missing_items(
        launch_blockers=[],
        failed_questions=failed_questions,
        limit=2,
    )

    assert result == [
        "Question 1",
        "Question 2",
    ]


def test_build_next_actions_maps_known_prompt_types():
    blockers = [
        {
            "prompt": "Has rollback strategy been documented?",
        },
        {
            "prompt": "Has escalation behavior been reviewed?",
        },
        {
            "prompt": "Are monitoring alerts defined?",
        },
    ]

    result = build_next_actions(
        launch_blockers=blockers,
        failed_questions=[],
    )

    assert "Document and validate a rollback plan." in result
    assert "Review and test escalation behavior for high-risk cases." in result
    assert "Set up monitoring dashboards and alert thresholds." in result


def test_build_next_actions_respects_limit():
    failed_questions = [
        {"prompt": "Question 1"},
        {"prompt": "Question 2"},
        {"prompt": "Question 3"},
    ]

    result = build_next_actions(
        launch_blockers=[],
        failed_questions=failed_questions,
        limit=2,
    )

    assert len(result) == 2


def test_build_recommendation_payload():
    assessment_result = {
        "overall_score": 88,
        "launch_blockers": [
            {
                "gate_title": "AI Quality",
                "prompt": "Has escalation behavior been reviewed?",
            }
        ],
        "failed_questions": [
            {
                "gate_title": "Customer Value",
                "prompt": "Has the customer journey been documented?",
            }
        ],
    }

    result = build_recommendation_payload(
        assessment_result
    )

    assert result["recommendation"] == "Ready for Beta"
    assert result["confidence"] == "Moderate"

    assert result["top_missing_items"] == [
        "AI Quality — Has escalation behavior been reviewed?",
        "Has the customer journey been documented?",
    ]

    assert (
        "Review and test escalation behavior for high-risk cases."
        in result["next_actions"]
    )