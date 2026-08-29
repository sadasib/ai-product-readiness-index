from __future__ import annotations

from typing import Any, Dict, List


def get_readiness_grade(overall_percentage: float) -> str:
    """Convert readiness percentage into the report grade."""
    if overall_percentage >= 95:
        return "A+"
    if overall_percentage >= 90:
        return "A"
    if overall_percentage >= 85:
        return "A-"
    if overall_percentage >= 80:
        return "B+"
    if overall_percentage >= 75:
        return "B"
    if overall_percentage >= 70:
        return "C"
    return "Needs Review"


def build_executive_summary(
    recommendation: str,
    launch_blockers: List[Dict[str, Any]],
    next_actions: List[str],
) -> str:
    """Create a concise executive summary for the report."""
    if recommendation == "Ready for Production":
        lead = (
            "The product demonstrates strong launch readiness and "
            "can proceed to production."
        )
    elif recommendation == "Ready for Beta":
        lead = (
            "The product demonstrates sufficient readiness for "
            "a controlled Beta launch."
        )
    elif recommendation == "Additional Review Required":
        lead = (
            "The product requires additional review before moving "
            "to a broader launch."
        )
    else:
        lead = (
            "The product is not currently ready for launch and "
            "requires material readiness improvements."
        )

    if launch_blockers:
        blocker_count = len(launch_blockers)
        blocker_text = (
            f" {blocker_count} critical launch blocker"
            f"{'s remain' if blocker_count != 1 else ' remains'}."
        )
    else:
        blocker_text = " No critical launch blockers remain."

    if next_actions:
        action_text = f" Highest-priority next action: {next_actions[0]}"
    else:
        action_text = ""

    return f"{lead}{blocker_text}{action_text}".strip()


def extract_critical_items(
    launch_blockers: List[Dict[str, Any]],
) -> List[str]:
    """Convert blocker objects into clean report strings."""
    critical_items: List[str] = []

    for blocker in launch_blockers:
        gate_title = str(blocker.get("gate_title", "")).strip()
        prompt = str(blocker.get("prompt", "")).strip()

        if gate_title and prompt:
            critical_items.append(f"{gate_title}: {prompt}")
        elif prompt:
            critical_items.append(prompt)

    return critical_items


def build_report_payload(
    assessment_result: Dict[str, Any],
    recommendation_payload: Dict[str, Any],
    product_name: str = "AI Product Assessment",
    version: str = "1.1",
) -> Dict[str, Any]:
    """
    Translate live application results into the payload required
    by the PDF exporter.
    """
    overall_score = float(
        assessment_result.get("overall_score", 0.0)
    )
    overall_max_score = float(
        assessment_result.get("overall_max_score", 100.0)
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
        recommendation_payload.get("confidence", "Low")
    )

    next_actions = [
        str(action)
        for action in recommendation_payload.get("next_actions", [])
        if str(action).strip()
    ]

    launch_blockers = assessment_result.get(
        "launch_blockers",
        [],
    )

    gate_results = assessment_result.get(
        "gate_results",
        [],
    )

    return {
        "product_name": product_name,
        "recommendation": recommendation,
        "readiness_score": overall_score,
        "readiness_max": overall_max_score,
        "grade": get_readiness_grade(overall_percentage),
        "confidence": confidence,
        "executive_summary": build_executive_summary(
            recommendation=recommendation,
            launch_blockers=launch_blockers,
            next_actions=next_actions,
        ),
        "gate_results": gate_results,
        "critical_items": extract_critical_items(
            launch_blockers
        ),
        "immediate_actions": next_actions,
        "version": version,
    }