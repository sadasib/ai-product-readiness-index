from __future__ import annotations

from typing import Any, Dict, List


def _format_question_label(question: Dict[str, Any]) -> str:
    """Build a clean label for a failed question."""
    gate_title = question.get("gate_title", "")
    prompt = question.get("prompt", "")
    if gate_title:
        return f"{gate_title}: {prompt}"
    return prompt


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
        prompt = blocker.get("prompt", "")
        if prompt and prompt not in items:
            items.append(prompt)

    for question in failed_questions:
        prompt = question.get("prompt", "")
        if prompt and prompt not in items:
            items.append(prompt)

    return items[:limit]


def build_next_actions(
    launch_blockers: List[Dict[str, Any]],
    failed_questions: List[Dict[str, Any]],
    recommendation: str,
    limit: int = 5,
) -> List[str]:
    """
    Convert missing items into human-friendly next actions.
    """
    actions: List[str] = []

    blocker_prompts = {item.get("prompt", "") for item in launch_blockers}

    for item in launch_blockers:
        prompt = item.get("prompt", "")
        if not prompt:
            continue

        if "evaluation" in prompt.lower():
            action = "Complete a structured human evaluation."
        elif "rollback" in prompt.lower():
            action = "Document a rollback strategy."
        elif "legal" in prompt.lower():
            action = "Obtain Legal approval."
        elif "security" in prompt.lower():
            action = "Complete a security review."
        elif "privacy" in prompt.lower():
            action = "Complete a privacy review."
        elif "monitor" in prompt.lower():
            action = "Set up monitoring dashboards and alerts."
        elif "policy" in prompt.lower():
            action = "Validate policy compliance with representative scenarios."
        elif "escalation" in prompt.lower():
            action = "Review and test escalation behavior."
        else:
            action = f"Address launch blocker: {prompt}"

        if action not in actions:
            actions.append(action)

    # Add a few broader actions from failed non-blocking questions.
    for item in failed_questions:
        prompt = item.get("prompt", "")
        if not prompt or prompt in blocker_prompts:
            continue

        lower = prompt.lower()
        if "hallucination" in lower:
            action = "Define and validate an acceptable hallucination threshold."
        elif "bias" in lower or "fairness" in lower:
            action = "Complete a bias and fairness review."
        elif "alert" in lower:
            action = "Define alert thresholds and incident triggers."
        elif "golden dataset" in lower or "evaluation set" in lower:
            action = "Create a representative evaluation dataset."
        elif "roi" in lower or "business" in lower:
            action = "Clarify the business case and expected ROI."
        elif "persona" in lower or "customer problem" in lower:
            action = "Refine the customer problem definition."
        elif "journey" in lower:
            action = "Document the customer journey more clearly."
        elif "metrics" in lower or "success" in lower:
            action = "Define measurable launch success criteria."
        elif "support" in lower:
            action = "Confirm support readiness and escalation coverage."
        elif "rollout" in lower:
            action = "Document and approve a phased rollout strategy."
        elif "sponsor" in lower:
            action = "Identify an accountable executive sponsor."
        else:
            action = f"Review and address: {prompt}"

        if action not in actions:
            actions.append(action)

    return actions[:limit]


def recommend_launch_state(
    overall_score: int,
    launch_blockers: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Return a human-readable recommendation block.
    """
    if launch_blockers:
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
    overall_score = int(assessment_result.get("overall_score", 0))
    launch_blockers = assessment_result.get("launch_blockers", [])
    failed_questions = assessment_result.get("failed_questions", [])

    launch_state = recommend_launch_state(overall_score, launch_blockers)
    top_missing_items = build_top_missing_items(launch_blockers, failed_questions)
    next_actions = build_next_actions(
        launch_blockers=launch_blockers,
        failed_questions=failed_questions,
        recommendation=launch_state["recommendation"],
    )

    return {
        "recommendation": launch_state["recommendation"],
        "confidence": launch_state["confidence"],
        "top_missing_items": top_missing_items,
        "next_actions": next_actions,
    }
