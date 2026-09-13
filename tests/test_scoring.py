from __future__ import annotations

from app.utils.scoring import (
    calculate_assessment,
    calculate_gate_score,
    determine_recommendation,
    get_launch_blockers,
    normalize_answer,
    score_answer,
)



ANSWER_SCORES = {
    "yes": 5,
    "partial": 3,
    "no": 0,
}


def test_normalize_answer():
    assert normalize_answer(" YES ") == "yes"
    assert normalize_answer("Partial") == "partial"
    assert normalize_answer(None) == ""
    assert normalize_answer(123) == "123"


def test_score_answer():
    assert score_answer("yes", ANSWER_SCORES) == 5
    assert score_answer("partial", ANSWER_SCORES) == 3
    assert score_answer("no", ANSWER_SCORES) == 0
    assert score_answer("unknown", ANSWER_SCORES) == 0
    assert score_answer(None, ANSWER_SCORES) == 0


def test_get_launch_blockers_only_returns_critical_non_yes_questions():
    questions_data = {
        "gates": [
            {
                "id": "g1",
                "title": "Customer Value",
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "Is the customer problem validated?",
                        "critical": True,
                    },
                    {
                        "id": "q2",
                        "prompt": "Is the journey documented?",
                        "critical": False,
                    },
                ],
            }
        ]
    }

    answers = {
        "q1": "partial",
        "q2": "no",
    }

    blockers = get_launch_blockers(
        questions_data,
        answers,
    )

    assert len(blockers) == 1
    assert blockers[0]["question_id"] == "q1"
    assert blockers[0]["answer"] == "partial"


def test_critical_yes_answer_is_not_a_blocker():
    questions_data = {
        "gates": [
            {
                "id": "g1",
                "title": "Customer Value",
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "Is the customer problem validated?",
                        "critical": True,
                    }
                ],
            }
        ]
    }

    answers = {"q1": "yes"}

    blockers = get_launch_blockers(
        questions_data,
        answers,
    )

    assert blockers == []


def test_missing_critical_answer_is_a_blocker():
    questions_data = {
        "gates": [
            {
                "id": "g1",
                "title": "Customer Value",
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "Is the customer problem validated?",
                        "critical": True,
                    }
                ],
            }
        ]
    }

    blockers = get_launch_blockers(
        questions_data,
        {},
    )

    assert len(blockers) == 1
    assert blockers[0]["answer"] == "no answer"


def test_calculate_gate_score():
    gate = {
        "id": "g1",
        "title": "Customer Value",
        "questions": [
            {
                "id": "q1",
                "prompt": "Question 1",
                "critical": False,
            },
            {
                "id": "q2",
                "prompt": "Question 2",
                "critical": False,
            },
        ],
    }

    answers = {
        "q1": "yes",
        "q2": "partial",
    }

    score, max_score, failed_questions = calculate_gate_score(
        gate=gate,
        answers=answers,
        answer_scores=ANSWER_SCORES,
    )

    assert score == 8
    assert max_score == 10

    assert len(failed_questions) == 1
    assert failed_questions[0]["question_id"] == "q2"
    assert failed_questions[0]["points"] == 3


def test_determine_recommendation_without_blockers():
    rules = [
        {
            "min_score": 90,
            "max_score": 100,
            "label": "Ready for Production",
        },
        {
            "min_score": 75,
            "max_score": 89.9,
            "label": "Ready for Beta",
        },
        {
            "min_score": 60,
            "max_score": 74.9,
            "label": "Additional Review Required",
        },
    ]

    assert (
        determine_recommendation(
            overall_score=95,
            blockers=[],
            recommendation_rules=rules,
        )
        == "Ready for Production"
    )

    assert (
        determine_recommendation(
            overall_score=85,
            blockers=[],
            recommendation_rules=rules,
        )
        == "Ready for Beta"
    )

    assert (
        determine_recommendation(
            overall_score=65,
            blockers=[],
            recommendation_rules=rules,
        )
        == "Additional Review Required"
    )


def test_critical_blocker_overrides_high_score():
    rules = [
        {
            "min_score": 90,
            "max_score": 100,
            "label": "Ready for Production",
        },
        {
            "min_score": 75,
            "max_score": 89.9,
            "label": "Ready for Beta",
        },
    ]

    blockers = [
        {
            "gate_id": "g1",
            "gate_title": "AI Quality",
            "question_id": "q1",
            "prompt": "Has escalation behavior been reviewed?",
            "answer": "no",
        }
    ]

    result = determine_recommendation(
        overall_score=96,
        blockers=blockers,
        recommendation_rules=rules,
        critical_failure_recommendation="Additional Review Required",
    )

    assert result == "Additional Review Required"


def test_calculate_assessment_normalizes_gate_scores_equally():
    questions_data = {
        "gates": [
            {
                "id": "g1",
                "title": "Gate One",
                "questions": [
                    {"id": "q1", "prompt": "Q1", "critical": False},
                ],
            },
            {
                "id": "g2",
                "title": "Gate Two",
                "questions": [
                    {"id": "q2", "prompt": "Q2", "critical": False},
                    {"id": "q3", "prompt": "Q3", "critical": False},
                ],
            },
        ]
    }

    scoring_rules = {
        "answer_scores": ANSWER_SCORES,
        "gate_max_score": 20,
        "recommendation_rules": [
            {
                "min_score": 90,
                "max_score": 100,
                "label": "Ready for Production",
            }
        ],
    }

    answers = {
        "q1": "yes",
        "q2": "yes",
        "q3": "yes",
    }

    result = calculate_assessment(
        questions_data,
        scoring_rules,
        answers,
    )

    assert result["overall_max_score"] == 40
    assert result["overall_score"] == 40
    assert result["overall_percentage"] == 100.0

    assert len(result["gate_results"]) == 2

    for gate in result["gate_results"]:
        assert gate["max_score"] == 20
        assert gate["percentage"] == 100.0


def test_sample_assessment_regression():
    from app.utils.scoring import score_sample_assessment

    result = score_sample_assessment()

    assert result["overall_score"] == 88.1
    assert result["overall_max_score"] == 100.0
    assert result["overall_percentage"] == 88.1

    assert len(result["gate_results"]) == 5
    assert len(result["launch_blockers"]) == 1