from __future__ import annotations

from typing import Any, Dict, List


def _unique_preserve_order(items: List[str]) -> List[str]:
    """Return unique, non-empty strings while preserving order."""
    seen = set()
    unique_items: List[str] = []

    for item in items:
        value = str(item).strip()
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            unique_items.append(value)

    return unique_items


def _format_missing_item(item: Dict[str, Any]) -> str:
    """Format a missing item for display in the UI."""
    gate_title = str(item.get("gate_title", "")).strip()
    prompt = str(item.get("prompt", "")).strip()

    if gate_title and prompt:
        return f"{gate_title} — {prompt}"
    if prompt:
        return prompt
    if gate_title:
        return gate_title
    return "Unspecified item"


def _action_from_prompt(prompt: str) -> str:
    """Convert a failed prompt into a human-friendly next action."""
    lower = prompt.lower()

    if "human evaluation" in lower or "evaluation" in lower:
        return "Complete a structured human evaluation on representative scenarios."
    if "rollback" in lower:
        return "Document and validate a rollback plan."
    if "legal" in lower:
        return "Obtain Legal approval before launch."
    if "security" in lower:
        return "Complete a security review."
    if "privacy" in lower:
        return "Complete a privacy review."
    if "monitor" in lower or "alert" in lower:
        return "Set up monitoring dashboards and alert thresholds."
    if "policy" in lower:
        return "Validate policy compliance with representative scenarios."
    if "escalation" in lower:
        return "Review and test escalation behavior for high-risk cases."
    if "golden dataset" in lower or "evaluation set" in lower:
        return "Create a representative evaluation dataset."
    if "roi" in lower or "business" in lower:
        return "Clarify the business case and expected ROI."
    if "persona" in lower or "customer problem" in lower:
        return "Refine the customer problem definition."
    if "journey" in lower:
        return "Document the customer journey more clearly."
    if "metrics" in lower or "success" in lower:
        return "Define measurable launch success criteria."
    if "support" in lower:
        return "Confirm support readiness and escalation coverage."
    if "rollout" in lower:
        return "Document and approve a phased rollout strategy."
    if "sponsor" in lower:
        return "Identify an accountable executive sponsor."

    return f"Review and address: {prompt}"


def build_top_missing_items(
    launch_blockers: List[Dict[str, Any]],
    failed_questions: List[Dict[str, Any]],
    limit: int = 5,
) -> List[str]:
    """
    Return a concise list of the most important missing items.

    Priority:
    1. Launch blockers
    2. Non-blocking failed questions
    """
    items: List[str] = []

    for blocker in launch_blockers:
        items.append(_format_missing_item(blocker))

    for question in failed_questions:
        prompt = str(question.get("prompt", "")).strip()
        if prompt:
            items.append(prompt)

    return _unique_preserve_order(items)[:limit]


def build_next_actions(
    launch_blockers: List[Dict[str, Any]],
    failed_questions: List[Dict[str, Any]],
    limit: int = 5,
) -> List[str]:
    """
    Convert missing items into concise, human-friendly next actions.
    """
    actions: List[str] = []

    for item in launch_blockers:
        prompt = str(item.get("prompt", "")).strip()
        if prompt:
            actions.append(_action_from_prompt(prompt))

    for item in failed_questions:
        prompt = str(item.get("prompt", "")).strip()
        if prompt:
            actions.append(_action_from_prompt(prompt))

    return _unique_preserve_order(actions)[:limit]


def recommend_launch_state(
    overall_score: float,
    launch_blockers: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Return a human-readable recommendation block.

    Critical blockers prevent a Production recommendation.
    """
    has_blockers = len(launch_blockers) > 0

    if has_blockers:
        if overall_score >= 90:
            recommendation = "Ready for Beta"
            confidence = "High"
        elif overall_score >= 75:
            recommendation = "Ready for Beta"
            confidence = "Moderate"
        elif overall_score >= 60:
            recommendation = "Additional Review Required"
            confidence = "Moderate"
        else:
            recommendation = "Not Ready"
            confidence = "Low"
    else:
        if overall_score >= 90:
            recommendation = "Ready for Production"
            confidence = "High"
        elif overall_score >= 75:
            recommendation = "Ready for Beta"
            confidence = "High"
        elif overall_score >= 60:
            recommendation = "Additional Review Required"
            confidence = "Moderate"
        else:
            recommendation = "Not Ready"
            confidence = "Low"

    return {
        "recommendation": recommendation,
        "confidence": confidence,
    }


def build_recommendation_payload(assessment_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a clean recommendation payload for the UI.
    """
    overall_score = float(assessment_result.get("overall_score", 0))
    launch_blockers = assessment_result.get("launch_blockers", [])
    failed_questions = assessment_result.get("failed_questions", [])

    launch_state = recommend_launch_state(overall_score, launch_blockers)
    top_missing_items = build_top_missing_items(launch_blockers, failed_questions)
    next_actions = build_next_actions(launch_blockers, failed_questions)

    return {
        "recommendation": launch_state["recommendation"],
        "confidence": launch_state["confidence"],
        "top_missing_items": top_missing_items,
        "next_actions": next_actions,
    }