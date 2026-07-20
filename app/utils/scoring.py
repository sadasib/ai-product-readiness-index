from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


def load_json(path: Path) -> Dict[str, Any]:
    """Load a JSON file and return its contents."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_answer(answer: Any) -> str:
    """Normalize answers to lowercase strings."""
    if answer is None:
        return ""
    return str(answer).strip().lower()


def score_answer(answer: Any, answer_scores: Dict[str, int]) -> int:
    """Convert a user answer to points."""
    normalized = normalize_answer(answer)
    return int(answer_scores.get(normalized, 0))


def get_launch_blockers(
    questions_data: Dict[str, Any],
    answers: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Return critical questions that were answered 'no' or left blank.
    """
    blockers: List[Dict[str, Any]] = []

    for gate in questions_data.get("gates", []):
        for question in gate.get("questions", []):
            if not question.get("critical", False):
                continue

            qid = question.get("id")
            answer = normalize_answer(answers.get(qid))

            if answer != "yes":
                blockers.append(
                    {
                        "gate_id": gate.get("id"),
                        "gate_title": gate.get("title"),
                        "question_id": qid,
                        "prompt": question.get("prompt"),
                        "answer": answer or "no answer",
                    }
                )

    return blockers


def calculate_gate_score(
    gate: Dict[str, Any],
    answers: Dict[str, Any],
    answer_scores: Dict[str, int],
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Score a single gate.
    Returns:
        (gate_score, gate_max_score, failed_questions)
    """
    questions = gate.get("questions", [])
    gate_max_score = len(questions) * int(max(answer_scores.values(), default=0))

    gate_score = 0
    failed_questions: List[Dict[str, Any]] = []

    for question in questions:
        qid = question.get("id")
        answer = answers.get(qid)
        points = score_answer(answer, answer_scores)
        gate_score += points

        if normalize_answer(answer) != "yes":
            failed_questions.append(
                {
                    "question_id": qid,
                    "prompt": question.get("prompt"),
                    "critical": bool(question.get("critical", False)),
                    "answer": normalize_answer(answer) or "no answer",
                    "points": points,
                }
            )

    return gate_score, gate_max_score, failed_questions


def determine_recommendation(
    overall_score: int,
    blockers: List[Dict[str, Any]],
    recommendation_rules: List[Dict[str, Any]],
    critical_failure_recommendation: str = "Additional Review Required",
) -> str:
    """
    Determine recommendation using score bands and launch blockers.
    """
    if blockers:
        return critical_failure_recommendation

    for rule in recommendation_rules:
        min_score = int(rule.get("min_score", 0))
        max_score = int(rule.get("max_score", 100))
        requires_no_launch_blockers = bool(rule.get("requires_no_launch_blockers", False))

        if min_score <= overall_score <= max_score:
            if requires_no_launch_blockers:
                return str(rule.get("label", "Additional Review Required"))
            return str(rule.get("label", "Additional Review Required"))

    return "Not Ready"


def calculate_assessment(
    questions_data: Dict[str, Any],
    scoring_rules: Dict[str, Any],
    answers: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate normalized gate scores, overall score, blockers,
    and launch recommendation.

    Every gate contributes equally to the final score, even when
    gates contain different numbers of questions.
    """
    answer_scores = scoring_rules.get("answer_scores", {})
    recommendation_rules = scoring_rules.get("recommendation_rules", [])
    critical_failure_recommendation = scoring_rules.get(
        "critical_failure_recommendation",
        "Additional Review Required",
    )

    target_gate_max = float(scoring_rules.get("gate_max_score", 20))
    gates = questions_data.get("gates", [])

    gate_results: List[Dict[str, Any]] = []
    total_score = 0.0
    all_failed_questions: List[Dict[str, Any]] = []

    for gate in gates:
        raw_score, raw_max_score, failed_questions = calculate_gate_score(
            gate=gate,
            answers=answers,
            answer_scores=answer_scores,
        )

        percentage = (
            round((raw_score / raw_max_score) * 100, 1)
            if raw_max_score
            else 0.0
        )

        normalized_score = round(
            (percentage / 100) * target_gate_max,
            1,
        )

        gate_results.append(
            {
                "gate_id": gate.get("id"),
                "gate_title": gate.get("title"),
                "description": gate.get("description", ""),
                "score": normalized_score,
                "max_score": target_gate_max,
                "raw_score": raw_score,
                "raw_max_score": raw_max_score,
                "percentage": percentage,
                "failed_questions": failed_questions,
            }
        )

        total_score += normalized_score
        all_failed_questions.extend(failed_questions)

    overall_max_score = round(target_gate_max * len(gates), 1)
    overall_score = round(total_score, 1)

    launch_blockers = get_launch_blockers(questions_data, answers)

    recommendation = determine_recommendation(
        overall_score=overall_score,
        blockers=launch_blockers,
        recommendation_rules=recommendation_rules,
        critical_failure_recommendation=critical_failure_recommendation,
    )

    return {
        "overall_score": overall_score,
        "overall_max_score": overall_max_score,
        "overall_percentage": (
            round((overall_score / overall_max_score) * 100, 1)
            if overall_max_score
            else 0.0
        ),
        "recommendation": recommendation,
        "gate_results": gate_results,
        "launch_blockers": launch_blockers,
        "failed_questions": all_failed_questions,
    }


def load_assessment_inputs(
    questions_path: Path | None = None,
    scoring_rules_path: Path | None = None,
    sample_assessment_path: Path | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Load all inputs needed for scoring.
    """
    questions_path = questions_path or (DATA_DIR / "questions.json")
    scoring_rules_path = scoring_rules_path or (DATA_DIR / "scoring_rules.json")
    sample_assessment_path = sample_assessment_path or (DATA_DIR / "sample_assessment.json")

    questions_data = load_json(questions_path)
    scoring_rules = load_json(scoring_rules_path)
    sample_assessment = load_json(sample_assessment_path)

    return questions_data, scoring_rules, sample_assessment


def score_sample_assessment() -> Dict[str, Any]:
    """
    Convenience helper for testing the sample assessment.
    """
    questions_data, scoring_rules, sample_assessment = load_assessment_inputs()
    answers = sample_assessment.get("answers", {})
    return calculate_assessment(questions_data, scoring_rules, answers)


if __name__ == "__main__":
    result = score_sample_assessment()
    print(json.dumps(result, indent=2))
