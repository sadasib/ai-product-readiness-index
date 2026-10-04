from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import streamlit as st

from utils.helpers import answer_label
from utils.product_context import (
    build_sample_product_context,
    create_product_context_snapshot,
    empty_product_context,
)


def get_gate_index(current_step: int) -> int:
    """Convert the current app step into a gate index."""
    return current_step - 2


def get_stage_label(
    current_step: int,
    gate_count: int,
) -> str:
    """Return the display label for the current application stage."""
    if current_step == 0:
        return "Not started"

    if current_step == 1:
        return "Product context"

    if 2 <= current_step <= gate_count + 1:
        return f"Gate {current_step - 1}/{gate_count}"

    return "Final report"


def clear_answer_state(
    questions_data: Dict[str, Any],
) -> None:
    """Clear current assessment answers and widget state."""
    st.session_state["answers"] = {}

    for gate in questions_data.get("gates", []):
        for question in gate.get("questions", []):
            widget_key = f"answer_{question.get('id')}"

            if widget_key in st.session_state:
                del st.session_state[widget_key]


def start_new_assessment(
    questions_data: Dict[str, Any],
) -> None:
    """
    Reset the current assessment while preserving history.

    A new product-context form is initialized separately.
    """
    clear_answer_state(
        questions_data
    )

    st.session_state["current_step"] = 1
    st.session_state["current_assessment_id"] = None
    st.session_state["selected_history_id"] = None

    st.session_state.pop(
        "report_payload",
        None,
    )

    st.session_state.pop(
        "report_pdf",
        None,
    )


def start_product_context() -> None:
    """Initialize a fresh product-context form."""
    context = empty_product_context()

    st.session_state["product_context"] = context

    st.session_state["product_context_name"] = (
        context["product_name"]
    )

    st.session_state["product_context_type"] = (
        context["product_type"]
    )

    st.session_state["product_context_stage"] = (
        context["launch_stage"]
    )

    st.session_state["product_context_owner"] = (
        context["assessment_owner"]
    )


def set_sample_answers(
    questions_data: Dict[str, Any],
    sample_assessment: Dict[str, Any],
) -> None:
    """Load sample answers and sample product context."""
    answers = sample_assessment.get(
        "answers",
        {},
    )

    st.session_state["answers"] = dict(
        answers
    )

    st.session_state["current_assessment_id"] = None
    st.session_state["selected_history_id"] = None

    st.session_state["product_context"] = (
        build_sample_product_context()
    )

    for gate in questions_data.get("gates", []):
        for question in gate.get("questions", []):
            qid = question.get("id")
            widget_key = f"answer_{qid}"

            raw_answer = answer_label(
                answers.get(qid)
            )

            st.session_state[widget_key] = (
                raw_answer
                if raw_answer in {
                    "Yes",
                    "Partial",
                    "No",
                }
                else "Select an answer"
            )


def generate_assessment_id() -> str:
    """Generate a unique ID for the current assessment."""
    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    return f"assessment_{timestamp}"


def get_current_product_context() -> Dict[str, str]:
    """Return a normalized snapshot of the current product context."""
    return create_product_context_snapshot(
        st.session_state.get(
            "product_context",
            empty_product_context(),
        )
    )